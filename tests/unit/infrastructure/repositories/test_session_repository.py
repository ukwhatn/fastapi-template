"""
セッションリポジトリの単体テスト
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.infrastructure.repositories.session_repository import SessionService


class TestSessionService:
    """セッションサービスのテスト"""

    def test_session_lifecycle(self, db_session: Session) -> None:
        """セッションのCRUDライフサイクル（作成→取得→更新→削除）"""
        service = SessionService(db_session)
        data = {"user_id": 123, "username": "testuser"}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        # 作成
        session_id, csrf_token = service.create_session(data, user_agent, client_ip)
        assert isinstance(session_id, str)
        assert isinstance(csrf_token, str)
        assert len(session_id) == 64
        assert len(csrf_token) == 64

        # 取得
        retrieved_data = service.get_session(session_id, user_agent, client_ip)
        assert retrieved_data is not None
        assert retrieved_data["user_id"] == 123
        assert retrieved_data["username"] == "testuser"

        # 更新
        updated_data = {"user_id": 123, "username": "updated"}
        result = service.update_session(session_id, updated_data, user_agent, client_ip)
        assert result is True

        retrieved_data = service.get_session(session_id, user_agent, client_ip)
        assert retrieved_data is not None
        assert retrieved_data["username"] == "updated"

        # 削除
        result = service.delete_session(session_id)
        assert result is True

        retrieved_data = service.get_session(session_id, user_agent, client_ip)
        assert retrieved_data is None

    def test_fingerprint_validation(self, db_session: Session) -> None:
        """フィンガープリント検証が正しく動作すること"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)

        # 正しいフィンガープリントで取得成功
        retrieved_data = service.get_session(session_id, user_agent, client_ip)
        assert retrieved_data is not None

        # 異なるUser-Agentで取得失敗
        retrieved_data = service.get_session(session_id, "Chrome/90.0", client_ip)
        assert retrieved_data is None

        # 異なるIPで取得失敗
        retrieved_data = service.get_session(session_id, user_agent, "192.168.1.1")
        assert retrieved_data is None

    def test_session_regeneration(self, db_session: Session) -> None:
        """セッションID再生成が正しく動作すること"""
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
        assert len(new_session_id) == 64
        assert len(new_csrf_token) == 64

        # 古いIDでは取得できない
        old_data = service.get_session(old_session_id, user_agent, client_ip)
        assert old_data is None

        # 新しいIDで取得成功
        new_data = service.get_session(new_session_id, user_agent, client_ip)
        assert new_data is not None
        assert new_data["user_id"] == 123

    def test_cleanup_expired_sessions(self, db_session: Session) -> None:
        """期限切れセッションがクリーンアップされること"""
        service = SessionService(db_session)
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        # セッション作成
        session_id, _ = service.create_session({"user_id": 123}, user_agent, client_ip)

        # 有効期限を過去に設定（直接DB操作）
        from app.infrastructure.database.models.session import Session as SessionModel

        session_model = (
            db_session.query(SessionModel)
            .filter(SessionModel.session_id == session_id)
            .first()
        )
        if session_model:
            session_model.expires_at = datetime.now() - timedelta(days=1)
            db_session.commit()

        # クリーンアップ実行
        deleted_count = service.cleanup_expired_sessions()
        assert deleted_count >= 1

        # 期限切れセッションは取得できない
        retrieved_data = service.get_session(session_id, user_agent, client_ip)
        assert retrieved_data is None
