"""
セッションリポジトリの単体テスト
"""

from typing import Any, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.infrastructure.repositories.session_repository import SessionService


class TestSessionService:
    """セッションサービスのテスト"""

    def test_create_session(self, db_session: Session) -> None:
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

    def test_get_session(self, db_session: Session) -> None:
        """セッションが取得できること"""
        service = SessionService(db_session)
        data: Dict[str, int] = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)
        retrieved_data = service.get_session(session_id, user_agent, client_ip)

        assert retrieved_data is not None
        assert retrieved_data["user_id"] == 123

    def test_get_session_with_wrong_fingerprint(self, db_session: Session) -> None:
        """フィンガープリントが異なる場合、セッションが取得できないこと"""
        service = SessionService(db_session)
        data: Dict[str, int] = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)

        # 異なるUser-Agentで取得試行
        retrieved_data = service.get_session(session_id, "Chrome/90.0", client_ip)
        assert retrieved_data is None

    def test_update_session(self, db_session: Session) -> None:
        """セッションが更新されること"""
        service = SessionService(db_session)
        data: Dict[str, int] = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)

        # データ更新
        new_data: Dict[str, Any] = {"user_id": 123, "username": "updated"}
        result = service.update_session(session_id, new_data, user_agent, client_ip)
        assert result is True

        # 更新されたデータを取得
        retrieved_data = service.get_session(session_id, user_agent, client_ip)
        assert retrieved_data is not None
        assert retrieved_data["username"] == "updated"

    def test_delete_session(self, db_session: Session) -> None:
        """セッションが削除されること"""
        service = SessionService(db_session)
        data: Dict[str, int] = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)

        # 削除
        result = service.delete_session(session_id)
        assert result is True

        # 削除後は取得できない
        retrieved_data = service.get_session(session_id, user_agent, client_ip)
        assert retrieved_data is None

    def test_regenerate_session_id(self, db_session: Session) -> None:
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


class TestSessionServiceEdgeCases:
    """セッションサービスの異常系・境界値テスト"""

    def test_get_nonexistent_session(self, db_session: Session) -> None:
        """存在しないセッションIDで取得するとNoneが返ること"""
        service = SessionService(db_session)
        result = service.get_session(
            "nonexistent-session-id", "Mozilla/5.0", "127.0.0.1"
        )
        assert result is None

    def test_update_nonexistent_session(self, db_session: Session) -> None:
        """存在しないセッションの更新はFalseが返ること"""
        service = SessionService(db_session)
        result = service.update_session(
            "nonexistent-session-id", {"data": "test"}, "Mozilla/5.0", "127.0.0.1"
        )
        assert result is False

    def test_update_with_wrong_fingerprint(self, db_session: Session) -> None:
        """フィンガープリントが異なる場合、更新できないこと"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)

        # 異なるUser-Agentで更新試行
        result = service.update_session(
            session_id, {"user_id": 456}, "Chrome/90.0", client_ip
        )
        assert result is False

        # NOTE: update時のフィンガープリントミスマッチでセッションが削除される実装になっている
        # これはセキュリティ対策として意図的な動作

    def test_delete_nonexistent_session(self, db_session: Session) -> None:
        """存在しないセッションの削除はFalseが返ること"""
        service = SessionService(db_session)
        result = service.delete_session("nonexistent-session-id")
        assert result is False

    def test_regenerate_nonexistent_session(self, db_session: Session) -> None:
        """存在しないセッションIDの再生成はNoneが返ること"""
        service = SessionService(db_session)
        result = service.regenerate_session_id(
            "nonexistent-session-id", "Mozilla/5.0", "127.0.0.1"
        )
        assert result is None

    def test_regenerate_with_wrong_fingerprint(self, db_session: Session) -> None:
        """フィンガープリントが異なる場合、セッションIDを再生成できないこと"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)

        # 異なるUser-Agentで再生成試行
        result = service.regenerate_session_id(session_id, "Chrome/90.0", client_ip)
        assert result is None

        # NOTE: regenerate時のフィンガープリントミスマッチでセッションが削除される実装になっている
        # これはセキュリティ対策として意図的な動作（セッション固定攻撃対策）

    def test_cleanup_expired_sessions(self, db_session: Session) -> None:
        """期限切れセッションがクリーンアップされること"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        # セッション作成
        session_id, _ = service.create_session(data, user_agent, client_ip)

        # 有効期限を過去に設定（直接DBを操作）
        from app.infrastructure.database.models.session import Session as SessionModel

        session = db_session.query(SessionModel).filter_by(session_id=session_id).first()
        assert session is not None
        session.expires_at = datetime.now() - timedelta(hours=1)
        db_session.commit()

        # クリーンアップ実行
        deleted_count = service.cleanup_expired_sessions()
        assert deleted_count >= 1

        # 期限切れセッションは取得できない
        retrieved_data = service.get_session(session_id, user_agent, client_ip)
        assert retrieved_data is None

    def test_get_expired_session(self, db_session: Session) -> None:
        """期限切れセッションは取得できないこと"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        # セッション作成
        session_id, _ = service.create_session(data, user_agent, client_ip)

        # 有効期限を過去に設定
        from app.infrastructure.database.models.session import Session as SessionModel

        session = db_session.query(SessionModel).filter_by(session_id=session_id).first()
        assert session is not None
        session.expires_at = datetime.now() - timedelta(hours=1)
        db_session.commit()

        # 期限切れセッションは取得できない
        retrieved_data = service.get_session(session_id, user_agent, client_ip)
        assert retrieved_data is None

    def test_create_session_with_empty_data(self, db_session: Session) -> None:
        """空のデータでセッション作成できること"""
        service = SessionService(db_session)
        data: Dict[str, Any] = {}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, csrf_token = service.create_session(data, user_agent, client_ip)
        assert isinstance(session_id, str)
        assert isinstance(csrf_token, str)

        # 取得できること
        retrieved_data = service.get_session(session_id, user_agent, client_ip)
        assert retrieved_data == {}

    def test_create_session_with_complex_data(self, db_session: Session) -> None:
        """複雑なデータ構造でセッション作成できること"""
        service = SessionService(db_session)
        data = {
            "user": {
                "id": 123,
                "profile": {
                    "name": "テストユーザー",
                    "roles": ["admin", "user"],
                    "settings": {"theme": "dark", "language": "ja"},
                },
            },
            "metadata": {
                "created_at": "2024-01-01T00:00:00Z",
                "last_login": "2024-01-02T12:00:00Z",
            },
        }
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)

        # 取得してデータが保持されていること
        retrieved_data = service.get_session(session_id, user_agent, client_ip)
        assert retrieved_data == data


class TestCSRFValidation:
    """CSRF検証のテスト"""

    def test_get_session_with_csrf_verification_success(self, db_session: Session) -> None:
        """正しいCSRFトークンでセッション取得成功"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, csrf_token = service.create_session(data, user_agent, client_ip)

        # CSRF検証付きで取得
        retrieved_data = service.get_session(
            session_id, user_agent, client_ip, verify_csrf=True, csrf_token=csrf_token
        )
        assert retrieved_data is not None
        assert retrieved_data["user_id"] == 123

    def test_get_session_with_csrf_verification_failure_wrong_token(self, db_session: Session) -> None:
        """間違ったCSRFトークンでセッション取得失敗"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)

        # 間違ったCSRFトークンで取得試行
        retrieved_data = service.get_session(
            session_id,
            user_agent,
            client_ip,
            verify_csrf=True,
            csrf_token="wrong-csrf-token",
        )
        assert retrieved_data is None

    def test_get_session_with_csrf_verification_failure_no_token(self, db_session: Session) -> None:
        """CSRFトークンなしで検証失敗"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, _ = service.create_session(data, user_agent, client_ip)

        # CSRFトークンなしで取得試行
        retrieved_data = service.get_session(
            session_id, user_agent, client_ip, verify_csrf=True, csrf_token=None
        )
        assert retrieved_data is None

    def test_get_csrf_token_success(self, db_session: Session) -> None:
        """CSRFトークン取得成功"""
        service = SessionService(db_session)
        data = {"user_id": 123}
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        session_id, expected_csrf_token = service.create_session(
            data, user_agent, client_ip
        )

        # CSRFトークン取得
        csrf_token = service.get_csrf_token(session_id)
        assert csrf_token == expected_csrf_token

    def test_get_csrf_token_nonexistent_session(self, db_session: Session) -> None:
        """存在しないセッションのCSRFトークン取得"""
        service = SessionService(db_session)

        csrf_token = service.get_csrf_token("nonexistent-session-id")
        assert csrf_token is None
