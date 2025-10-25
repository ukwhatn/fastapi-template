"""
pytest設定と共通フィクスチャ
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from cryptography.fernet import Fernet


def pytest_configure(config):
    """
    pytest実行前の設定

    暗号化キーをモジュールインポート前に設定する必要があるため、
    フィクスチャではなくpytest_configureフックで設定
    """
    # テスト用暗号化キーを設定
    key = Fernet.generate_key().decode()
    os.environ["SESSION_ENCRYPTION_KEY"] = key


# pytest_configure後にインポート（環境変数設定後にモジュールをロード）
from app.main import app
from app.infrastructure.database.models import Base
from app.infrastructure.database import get_db


# テスト用インメモリデータベース
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    テスト用DBセッション
    各テストごとに新しいセッションを作成し、テスト後にロールバック
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    テスト用FastAPIクライアント
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def api_key():
    """
    テスト用APIキー
    """
    from app.core.config import get_settings

    settings = get_settings()
    return settings.API_KEY
