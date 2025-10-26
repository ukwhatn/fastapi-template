"""
pytest設定と共通フィクスチャ（PostgreSQLベース）
"""

import os
from typing import Any, Generator

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from tests.helpers import (
    create_test_database,
    drop_test_database,
    generate_test_db_name,
    run_migrations,
)


def pytest_configure(config: Any) -> None:
    """
    pytest実行前の設定

    暗号化キーをモジュールインポート前に設定する必要があるため、
    フィクスチャではなくpytest_configureフックで設定
    """
    # テスト用暗号化キーを設定
    key = Fernet.generate_key().decode()
    os.environ["SESSION_ENCRYPTION_KEY"] = key


# pytest_configure後にインポート（環境変数設定後にモジュールをロード）
from app.core.config import get_settings  # noqa: E402
from app.infrastructure.database import get_db  # noqa: E402
from app.main import app  # noqa: E402

# テスト用データベース名（session scope）
_test_db_name: str | None = None


@pytest.fixture(scope="session")
def test_database() -> Generator[str, None, None]:
    """
    テスト用PostgreSQLデータベースを作成・削除する。

    session scopeなので、全テスト実行前に1回だけ作成され、
    全テスト終了後に削除される。

    Yields:
        データベース名
    """
    global _test_db_name

    # ランダムなDB名を生成
    _test_db_name = generate_test_db_name()

    # DB作成
    create_test_database(_test_db_name)

    # database_urlを構築
    settings = get_settings()
    database_url = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{_test_db_name}"
        f"?gssencmode=disable"
    )

    # マイグレーション実行
    run_migrations(database_url)

    # 環境変数を設定（integration testでlifespanイベントが正しいDBを使うように）
    original_db_name = os.environ.get("POSTGRES_DB")
    os.environ["POSTGRES_DB"] = _test_db_name

    # get_settings()のキャッシュをクリア（環境変数変更を反映）
    get_settings.cache_clear()

    yield _test_db_name

    # 環境変数を元に戻す
    if original_db_name is not None:
        os.environ["POSTGRES_DB"] = original_db_name
    else:
        os.environ.pop("POSTGRES_DB", None)

    # DB削除
    drop_test_database(_test_db_name)
    _test_db_name = None


@pytest.fixture(scope="session")
def test_engine(test_database: str) -> Generator[Engine, None, None]:
    """
    テスト用SQLAlchemy Engineを作成する。

    Args:
        test_database: テスト用データベース名

    Yields:
        SQLAlchemy Engine
    """
    settings = get_settings()
    database_url = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{test_database}"
        f"?gssencmode=disable"
    )

    engine = create_engine(database_url, echo=False)

    yield engine

    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """
    テスト用DBセッション（トランザクションベース）

    各テストごとにトランザクションを開始し、テスト後にロールバックする。
    これにより、テスト間のデータ分離を実現しつつ、高速な実行が可能。

    Args:
        test_engine: テスト用Engine

    Yields:
        SQLAlchemy Session
    """
    # コネクションを取得
    connection = test_engine.connect()

    # トランザクション開始
    transaction = connection.begin()

    # セッション作成
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=connection
    )
    session = TestingSessionLocal()

    # ネストトランザクション（SAVEPOINT）サポート
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session: Session, transaction: Any) -> None:
        """トランザクション終了後にSAVEPOINTを再開始"""
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    # 初回のSAVEPOINT開始
    session.begin_nested()

    yield session

    # クリーンアップ
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    テスト用FastAPIクライアント

    Args:
        db_session: テスト用DBセッション

    Yields:
        FastAPI TestClient
    """

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def api_key() -> str:
    """
    テスト用APIキー

    Returns:
        APIキー文字列
    """
    settings = get_settings()
    return settings.API_KEY
