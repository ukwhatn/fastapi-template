"""
セッションヘルパー関数の単体テスト（DB不要）
"""

from unittest.mock import Mock

from fastapi import Request


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
