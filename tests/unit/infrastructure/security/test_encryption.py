"""
セキュリティ機能（暗号化・トークン生成）の単体テスト
"""

import pytest
from cryptography.fernet import Fernet
from app.infrastructure.security.encryption import (
    SessionEncryption,
    generate_fingerprint,
    verify_fingerprint,
)


class TestSessionEncryption:
    """SessionEncryptionクラスのテスト"""

    def test_encryption_and_decryption(self) -> None:
        """暗号化と復号化が正しく動作すること"""
        key = Fernet.generate_key().decode()
        encryptor = SessionEncryption(encryption_key=key)

        # 暗号化が有効
        assert encryptor.enabled is True
        assert encryptor.cipher is not None

        # データの暗号化→復号化
        data = {"user_id": 123, "username": "testuser"}
        encrypted = encryptor.encrypt(data)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == data
        # 暗号化されたデータは元のデータとは異なる
        assert encrypted != str(data)

    def test_invalid_data_decryption_fails(self) -> None:
        """無効なデータの復号化は失敗すること"""
        key = Fernet.generate_key().decode()
        encryptor = SessionEncryption(encryption_key=key)

        with pytest.raises(Exception):
            encryptor.decrypt("invalid-encrypted-data")


class TestFingerprint:
    """セッションフィンガープリントのテスト"""

    def test_fingerprint_validation(self) -> None:
        """フィンガープリント検証が正しく動作すること"""
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"

        # フィンガープリント生成
        fingerprint = generate_fingerprint(user_agent, client_ip)
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64  # SHA256ハッシュ

        # 正しい情報で検証成功
        assert verify_fingerprint(fingerprint, user_agent, client_ip) is True

        # 異なるUser-Agentで検証失敗
        assert verify_fingerprint(fingerprint, "Chrome/90.0", client_ip) is False

        # 異なるIPで検証失敗
        assert verify_fingerprint(fingerprint, user_agent, "192.168.1.1") is False
