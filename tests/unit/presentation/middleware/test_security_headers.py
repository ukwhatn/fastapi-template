"""
セキュリティヘッダーミドルウェアの単体テスト

Note: ミドルウェアの実装はasyncだが、テストではモジュールレベルの設定値のテストに焦点を当てるため、
実際の非同期実行はintegration testで検証する
"""

from typing import Any


class TestSecurityHeadersMiddlewareConfig:
    """SecurityHeadersMiddlewareの設定テスト"""

    def test_security_headers_enabled_config(self, monkeypatch: Any) -> None:
        """SECURITY_HEADERS=Trueの場合、設定が正しく読み込まれること"""
        from cryptography.fernet import Fernet

        monkeypatch.setenv("SECURITY_HEADERS", "true")
        monkeypatch.setenv("SESSION_ENCRYPTION_KEY", Fernet.generate_key().decode())

        from app.core.config import get_settings

        get_settings.cache_clear()

        settings = get_settings()

        assert settings.SECURITY_HEADERS is True

        get_settings.cache_clear()

    def test_security_headers_disabled_config(self, monkeypatch: Any) -> None:
        """SECURITY_HEADERS=Falseの場合、設定が正しく読み込まれること"""
        from cryptography.fernet import Fernet

        monkeypatch.setenv("SECURITY_HEADERS", "false")
        monkeypatch.setenv("SESSION_ENCRYPTION_KEY", Fernet.generate_key().decode())

        from app.core.config import get_settings

        get_settings.cache_clear()

        settings = get_settings()

        assert settings.SECURITY_HEADERS is False

        get_settings.cache_clear()

    def test_custom_csp_policy_config(self, monkeypatch: Any) -> None:
        """カスタムCSPポリシーが設定できること"""
        from cryptography.fernet import Fernet

        custom_csp = "default-src 'self'; script-src 'self' 'unsafe-inline'"
        monkeypatch.setenv("CSP_POLICY", custom_csp)
        monkeypatch.setenv("SESSION_ENCRYPTION_KEY", Fernet.generate_key().decode())

        from app.core.config import get_settings

        get_settings.cache_clear()

        settings = get_settings()

        assert settings.CSP_POLICY == custom_csp

        get_settings.cache_clear()
