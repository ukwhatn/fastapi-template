"""バックアップ機能テスト用フィクスチャ"""

from datetime import UTC, datetime
from typing import Generator

import pytest
from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.models.session import Session as SessionModel


@pytest.fixture
def sample_session_data(
    test_engine: Engine,
) -> Generator[list[SessionModel], None, None]:
    """
    テスト用のサンプルセッションデータを作成する。

    トランザクション外でデータをコミットするため、create_backup()が
    新しい接続から読み取れるようにする。

    Args:
        test_engine: テスト用Engine

    Yields:
        作成されたSessionモデルのリスト
    """
    TestSessionLocal = sessionmaker(bind=test_engine)
    db = TestSessionLocal()

    try:
        sessions = [
            SessionModel(
                session_id="test_session_1",
                data="encrypted_data_1",
                expires_at=datetime.now(UTC),
                fingerprint="fingerprint_1",
                csrf_token="csrf_token_1",
            ),
            SessionModel(
                session_id="test_session_2",
                data="encrypted_data_2",
                expires_at=datetime.now(UTC),
                fingerprint="fingerprint_2",
                csrf_token="csrf_token_2",
            ),
            SessionModel(
                session_id="test_session_3",
                data="encrypted_data_3",
                expires_at=datetime.now(UTC),
                fingerprint="fingerprint_3",
                csrf_token="csrf_token_3",
            ),
        ]

        for session in sessions:
            db.add(session)
        db.commit()

        yield sessions

    finally:
        # クリーンアップ
        db.execute(
            delete(SessionModel).where(
                SessionModel.session_id.in_([
                    "test_session_1",
                    "test_session_2",
                    "test_session_3",
                ])
            )
        )
        db.commit()
        db.close()
