"""
セッションリポジトリの単体テスト
"""

import pytest
from datetime import datetime, timedelta
from app.infrastructure.repositories.session_repository import SessionService


class TestSessionService:
    """セッションサービスのテスト"""

    def test_create_session(self, db_session):
        """セッションが作成されること"""
        service = SessionService(db_session)
        data = {"user_id": 123, "username": "testuser"}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, csrf_token = service.create_session(data, user_agent, client_ip)

        assert isinstance(session_id, str)
        assert isinstance(csrf_token, str)
        assert len(session_id) == 64
        assert len(csrf_token) == 64

    def test_get_session(self, db_session):
        """セッションが取得できること"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)
        retrieved_data = service.get_session(session_id, user_agent, client_ip)

        assert retrieved_data is not None
        assert retrieved_data["user_id"] == 123

    def test_get_session_with_wrong_fingerprint(self, db_session):
        """フィンガープリントが異なる場合、セッションが取得できないこと"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)

        # 異なるUser-Agentで取得試行
        retrieved_data = service.get_session(session_id, "Chrome/90.0", client_ip)
        assert retrieved_data is None

    def test_update_session(self, db_session):
        """セッションが更新されること"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)

        # データ更新
        new_data = {"user_id": 123, "username": "updated"}
        result = service.update_session(session_id, new_data, user_agent, client_ip)
        assert result is True

        # 更新されたデータを取得
        retrieved_data = service.get_session(session_id, user_agent, client_ip)
        assert retrieved_data["username"] == "updated"

    def test_delete_session(self, db_session):
        """セッションが削除されること"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)

        # 削除
        result = service.delete_session(session_id)
        assert result is True

        # 削除後は取得できない
        retrieved_data = service.get_session(session_id, user_agent, client_ip)
        assert retrieved_data is None

    def test_regenerate_session_id(self, db_session):
        """セッションIDが再生成されること"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        old_session_id, _ = service.create_session(data, user_agent, client_ip)

        # セッションID再生成
        result = service.regenerate_session_id(old_session_id, user_agent, client_ip)
        assert result is not None

        new_session_id, new_csrf_token = result
        assert new_session_id != old_session_id

        # 古いセッションIDでは取得できない
        old_data = service.get_session(old_session_id, user_agent, client_ip)
        assert old_data is None

        # 新しいセッションIDで取得できる
        new_data = service.get_session(new_session_id, user_agent, client_ip)
        assert new_data is not None
        assert new_data["user_id"] == 123
