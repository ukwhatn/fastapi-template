"""
セキュリティ機能の単体テスト
"""

import pytest
from app.infrastructure.security.encryption import (
    SessionEncryption,
    generate_csrf_token,
    generate_session_id,
    generate_fingerprint,
    verify_fingerprint,
)


class TestSessionEncryption:
    """セッション暗号化のテスト"""

    def test_generate_session_id(self):
        """セッションIDが生成されること"""
        session_id = generate_session_id()
        assert isinstance(session_id, str)
        assert len(session_id) == 64  # 32バイト * 2 (hex)

    def test_generate_csrf_token(self):
        """CSRFトークンが生成されること"""
        csrf_token = generate_csrf_token()
        assert isinstance(csrf_token, str)
        assert len(csrf_token) == 64  # 32バイト * 2 (hex)

    def test_session_id_uniqueness(self):
        """セッションIDがユニークであること"""
        id1 = generate_session_id()
        id2 = generate_session_id()
        assert id1 != id2


class TestFingerprint:
    """セッションフィンガープリントのテスト"""

    def test_generate_fingerprint(self):
        """フィンガープリントが生成されること"""
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"
        fingerprint = generate_fingerprint(user_agent, client_ip)
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64  # SHA256ハッシュ

    def test_fingerprint_consistency(self):
        """同じ入力で同じフィンガープリントが生成されること"""
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"
        fp1 = generate_fingerprint(user_agent, client_ip)
        fp2 = generate_fingerprint(user_agent, client_ip)
        assert fp1 == fp2

    def test_fingerprint_difference(self):
        """異なる入力で異なるフィンガープリントが生成されること"""
        fp1 = generate_fingerprint("Mozilla/5.0", "127.0.0.1")
        fp2 = generate_fingerprint("Chrome/90.0", "127.0.0.1")
        assert fp1 != fp2

    def test_verify_fingerprint_success(self):
        """フィンガープリント検証が成功すること"""
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"
        fingerprint = generate_fingerprint(user_agent, client_ip)
        assert verify_fingerprint(fingerprint, user_agent, client_ip) is True

    def test_verify_fingerprint_failure(self):
        """フィンガープリント検証が失敗すること"""
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"
        fingerprint = generate_fingerprint(user_agent, client_ip)
        # 異なるUser-Agentで検証
        assert verify_fingerprint(fingerprint, "Chrome/90.0", client_ip) is False
