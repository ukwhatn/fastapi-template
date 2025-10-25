"""
セッションヘルパー関数の単体テスト
"""

from unittest.mock import Mock, MagicMock
from fastapi import Request, Response
from sqlalchemy.orm import Session


class TestIPAndUserAgentExtraction:
    """IP取得・User-Agent取得のテスト"""

    def test_get_client_ip_from_header(self) -> None:
        """X-Forwarded-Forヘッダーからクライアント IPを取得できること"""
        from app.utils.session_helper import get_client_ip

        request = Mock(spec=Request)
        request.headers.get.return_value = "203.0.113.1, 198.51.100.1"
        request.client = None

        ip = get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_get_client_ip_from_client_host(self) -> None:
        """X-Forwarded-Forがない場合、client.hostから取得すること"""
        from app.utils.session_helper import get_client_ip

        request = Mock(spec=Request)
        request.headers.get.return_value = None
        mock_client = Mock()
        mock_client.host = "192.168.1.1"
        request.client = mock_client

        ip = get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_none_when_no_client(self) -> None:
        """clientがない場合、Noneを返すこと"""
        from app.utils.session_helper import get_client_ip

        request = Mock(spec=Request)
        request.headers.get.return_value = None
        request.client = None

        ip = get_client_ip(request)
        assert ip is None

    def test_get_user_agent(self) -> None:
        """User-Agentヘッダーを取得できること"""
        from app.utils.session_helper import get_user_agent

        request = Mock(spec=Request)
        request.headers.get.return_value = "Mozilla/5.0"

        user_agent = get_user_agent(request)
        assert user_agent == "Mozilla/5.0"

    def test_get_user_agent_none(self) -> None:
        """User-Agentヘッダーがない場合、Noneを返すこと"""
        from app.utils.session_helper import get_user_agent

        request = Mock(spec=Request)
        request.headers.get.return_value = None

        user_agent = get_user_agent(request)
        assert user_agent is None


class TestSessionCookieOperations:
    """Cookieを使ったセッション操作のテスト"""

    def test_create_session(self, db_session: Session) -> None:
        """セッションを作成してCookieに設定できること"""
        from app.utils.session_helper import create_session

        request = Mock(spec=Request)
        request.headers.get.return_value = "Mozilla/5.0"
        mock_client = Mock()
        mock_client.host = "127.0.0.1"
        request.client = mock_client

        response = Mock(spec=Response)

        data = {"user_id": 123}
        session_id, csrf_token = create_session(db_session, response, request, data)

        assert isinstance(session_id, str)
        assert isinstance(csrf_token, str)
        assert len(session_id) == 64
        assert len(csrf_token) == 64
        # Cookieが設定されたことを確認
        response.set_cookie.assert_called_once()

    def test_get_session_data(self, db_session: Session) -> None:
        """セッションデータをCookieから取得できること"""
        from app.utils.session_helper import create_session, get_session_data

        # セッション作成
        request = Mock(spec=Request)
        request.headers.get.return_value = "Mozilla/5.0"
        mock_client = Mock()
        mock_client.host = "127.0.0.1"
        request.client = mock_client

        response = Mock(spec=Response)
        data = {"user_id": 123}
        session_id, csrf_token = create_session(db_session, response, request, data)

        # セッション取得 - cookies.getをモック
        mock_cookies = MagicMock()
        mock_cookies.get.return_value = session_id
        request.cookies = mock_cookies

        retrieved_data = get_session_data(db_session, request)

        assert retrieved_data is not None
        assert retrieved_data["user_id"] == 123

    def test_get_session_data_no_cookie(self, db_session: Session) -> None:
        """Cookieがない場合、Noneを返すこと"""
        from app.utils.session_helper import get_session_data

        request = Mock(spec=Request)
        mock_cookies = MagicMock()
        mock_cookies.get.return_value = None
        request.cookies = mock_cookies

        data = get_session_data(db_session, request)
        assert data is None

    def test_update_session_data(self, db_session: Session) -> None:
        """セッションデータを更新できること"""
        from app.utils.session_helper import create_session, update_session_data

        # セッション作成
        request = Mock(spec=Request)
        request.headers.get.return_value = "Mozilla/5.0"
        mock_client = Mock()
        mock_client.host = "127.0.0.1"
        request.client = mock_client

        response = Mock(spec=Response)
        data = {"user_id": 123}
        session_id, csrf_token = create_session(db_session, response, request, data)

        # セッション更新
        mock_cookies = MagicMock()
        mock_cookies.get.return_value = session_id
        request.cookies = mock_cookies

        new_data = {"user_id": 123, "username": "updated"}
        result = update_session_data(db_session, request, new_data)

        assert result is True

    def test_update_session_data_no_cookie(self, db_session: Session) -> None:
        """Cookieがない場合、Falseを返すこと"""
        from app.utils.session_helper import update_session_data

        request = Mock(spec=Request)
        mock_cookies = MagicMock()
        mock_cookies.get.return_value = None
        request.cookies = mock_cookies

        result = update_session_data(db_session, request, {"data": "test"})
        assert result is False

    def test_delete_session(self, db_session: Session) -> None:
        """セッションを削除してCookieをクリアできること"""
        from app.utils.session_helper import create_session, delete_session

        # セッション作成
        request = Mock(spec=Request)
        request.headers.get.return_value = "Mozilla/5.0"
        mock_client = Mock()
        mock_client.host = "127.0.0.1"
        request.client = mock_client

        response = Mock(spec=Response)
        data = {"user_id": 123}
        session_id, csrf_token = create_session(db_session, response, request, data)

        # セッション削除
        mock_cookies = MagicMock()
        mock_cookies.get.return_value = session_id
        request.cookies = mock_cookies

        result = delete_session(db_session, request, response)

        assert result is True
        # delete_cookieが1回呼ばれる
        response.delete_cookie.assert_called_once()

    def test_delete_session_no_cookie(self, db_session: Session) -> None:
        """Cookieがない場合、Falseを返すこと"""
        from app.utils.session_helper import delete_session

        request = Mock(spec=Request)
        mock_cookies = MagicMock()
        mock_cookies.get.return_value = None
        request.cookies = mock_cookies

        response = Mock(spec=Response)

        result = delete_session(db_session, request, response)
        assert result is False

    def test_regenerate_session_id(self, db_session: Session) -> None:
        """セッションIDを再生成できること"""
        from app.utils.session_helper import create_session, regenerate_session_id

        # セッション作成
        request = Mock(spec=Request)
        request.headers.get.return_value = "Mozilla/5.0"
        mock_client = Mock()
        mock_client.host = "127.0.0.1"
        request.client = mock_client

        response = Mock(spec=Response)
        data = {"user_id": 123}
        old_session_id, old_csrf_token = create_session(
            db_session, response, request, data
        )

        # セッションID再生成
        mock_cookies = MagicMock()
        mock_cookies.get.return_value = old_session_id
        request.cookies = mock_cookies

        result = regenerate_session_id(db_session, request, response)

        assert result is not None
        new_session_id, new_csrf_token = result
        assert new_session_id != old_session_id
        # set_cookieが2回呼ばれる（create + regenerate）
        assert response.set_cookie.call_count == 2

    def test_regenerate_session_id_no_cookie(self, db_session: Session) -> None:
        """Cookieがない場合、Noneを返すこと"""
        from app.utils.session_helper import regenerate_session_id

        request = Mock(spec=Request)
        mock_cookies = MagicMock()
        mock_cookies.get.return_value = None
        request.cookies = mock_cookies

        response = Mock(spec=Response)

        result = regenerate_session_id(db_session, request, response)
        assert result is None

    def test_get_csrf_token(self, db_session: Session) -> None:
        """CSRFトークンを取得できること"""
        from app.utils.session_helper import create_session, get_csrf_token

        # セッション作成
        request = Mock(spec=Request)
        request.headers.get.return_value = "Mozilla/5.0"
        mock_client = Mock()
        mock_client.host = "127.0.0.1"
        request.client = mock_client

        response = Mock(spec=Response)
        data = {"user_id": 123}
        session_id, expected_csrf = create_session(db_session, response, request, data)

        # CSRFトークン取得
        mock_cookies = MagicMock()
        mock_cookies.get.return_value = session_id
        request.cookies = mock_cookies

        csrf_token = get_csrf_token(db_session, request)

        assert csrf_token == expected_csrf

    def test_get_csrf_token_no_cookie(self, db_session: Session) -> None:
        """Cookieがない場合、Noneを返すこと"""
        from app.utils.session_helper import get_csrf_token

        request = Mock(spec=Request)
        mock_cookies = MagicMock()
        mock_cookies.get.return_value = None
        request.cookies = mock_cookies

        csrf_token = get_csrf_token(db_session, request)
        assert csrf_token is None
