"""
セキュリティ機能（暗号化・トークン生成）の単体テスト
"""

from typing import Any, Dict
import pytest
import json
from cryptography.fernet import Fernet
from app.infrastructure.security.encryption import (
    SessionEncryption,
    get_session_encryption,
    generate_csrf_token,
    generate_session_id,
    generate_fingerprint,
    verify_fingerprint,
)


class TestTokenGeneration:
    """トークン生成機能のテスト"""

    def test_generate_session_id(self) -> None:
        """セッションIDが生成されること"""
        session_id = generate_session_id()
        assert isinstance(session_id, str)
        assert len(session_id) == 64  # 32バイト * 2 (hex)

    def test_generate_csrf_token(self) -> None:
        """CSRFトークンが生成されること"""
        csrf_token = generate_csrf_token()
        assert isinstance(csrf_token, str)
        assert len(csrf_token) == 64  # 32バイト * 2 (hex)

    def test_session_id_uniqueness(self) -> None:
        """セッションIDがユニークであること"""
        id1 = generate_session_id()
        id2 = generate_session_id()
        assert id1 != id2

    def test_csrf_token_uniqueness(self) -> None:
        """CSRFトークンがユニークであること"""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        assert token1 != token2


class TestFingerprint:
    """セッションフィンガープリントのテスト"""

    def test_generate_fingerprint(self) -> None:
        """フィンガープリントが生成されること"""
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"
        fingerprint = generate_fingerprint(user_agent, client_ip)
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64  # SHA256ハッシュ

    def test_fingerprint_consistency(self) -> None:
        """同じ入力で同じフィンガープリントが生成されること"""
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"
        fp1 = generate_fingerprint(user_agent, client_ip)
        fp2 = generate_fingerprint(user_agent, client_ip)
        assert fp1 == fp2

    def test_fingerprint_difference_by_user_agent(self) -> None:
        """異なるUser-Agentで異なるフィンガープリントが生成されること"""
        fp1 = generate_fingerprint("Mozilla/5.0", "127.0.0.1")
        fp2 = generate_fingerprint("Chrome/90.0", "127.0.0.1")
        assert fp1 != fp2

    def test_fingerprint_difference_by_ip(self) -> None:
        """異なるIPで異なるフィンガープリントが生成されること"""
        fp1 = generate_fingerprint("Mozilla/5.0", "127.0.0.1")
        fp2 = generate_fingerprint("Mozilla/5.0", "192.168.1.1")
        assert fp1 != fp2

    def test_verify_fingerprint_success(self) -> None:
        """フィンガープリント検証が成功すること"""
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"
        fingerprint = generate_fingerprint(user_agent, client_ip)
        assert verify_fingerprint(fingerprint, user_agent, client_ip) is True

    def test_verify_fingerprint_failure_wrong_user_agent(self) -> None:
        """異なるUser-Agentでフィンガープリント検証が失敗すること"""
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"
        fingerprint = generate_fingerprint(user_agent, client_ip)
        # 異なるUser-Agentで検証
        assert verify_fingerprint(fingerprint, "Chrome/90.0", client_ip) is False

    def test_verify_fingerprint_failure_wrong_ip(self) -> None:
        """異なるIPでフィンガープリント検証が失敗すること"""
        user_agent = "Mozilla/5.0"
        client_ip = "127.0.0.1"
        fingerprint = generate_fingerprint(user_agent, client_ip)
        # 異なるIPで検証
        assert verify_fingerprint(fingerprint, user_agent, "192.168.1.1") is False


class TestSessionEncryption:
    """SessionEncryptionクラスのテスト

    DI（依存性注入）パターンを使用して、明示的なキー指定でテスト
    """

    def test_encryption_with_explicit_key(self) -> None:
        """明示的な暗号化キーでインスタンス化できること"""
        key = Fernet.generate_key().decode()
        encryptor = SessionEncryption(encryption_key=key)

        assert encryptor.enabled is True
        assert encryptor.cipher is not None
        assert encryptor.encryption_key == key

    def test_encryption_enabled_with_explicit_key(self) -> None:
        """明示的なキーを指定した場合、暗号化が有効になること"""
        key = Fernet.generate_key().decode()
        encryptor = SessionEncryption(encryption_key=key)

        data: Dict[str, str] = {"test": "data"}
        encrypted = encryptor.encrypt(data)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == data
        # 暗号化されているので元のJSONとは異なる
        assert encrypted != json.dumps(data)

    def test_encryption_without_key_uses_settings(self, monkeypatch: Any) -> None:
        """キーを指定しない場合、設定から取得すること"""
        # テスト用キーを環境変数に設定
        test_key = Fernet.generate_key().decode()
        monkeypatch.setenv("SESSION_ENCRYPTION_KEY", test_key)

        # Settings再読み込み
        from app.core.config import get_settings

        get_settings.cache_clear()

        encryptor = SessionEncryption()

        assert encryptor.enabled is True
        assert encryptor.cipher is not None

        # キャッシュクリア
        get_settings.cache_clear()

    def test_encryption_with_invalid_key_disables_encryption(self) -> None:
        """無効なキーの場合、暗号化が無効になること"""
        encryptor = SessionEncryption(encryption_key="invalid-key")

        assert encryptor.enabled is False
        assert encryptor.cipher is None

    def test_encryption_with_none_key_and_no_env_disables_encryption(self, monkeypatch: Any) -> None:
        """キーがNoneかつ環境変数も無い場合、暗号化が無効になること"""
        # 環境変数を削除
        monkeypatch.delenv("SESSION_ENCRYPTION_KEY", raising=False)

        # Settings再読み込みのためにget_settings()のキャッシュをクリア
        from app.core.config import get_settings

        get_settings.cache_clear()

        encryptor = SessionEncryption()

        assert encryptor.enabled is False
        assert encryptor.cipher is None

        # キャッシュを再度クリア（他のテストへの影響を防ぐ）
        get_settings.cache_clear()

    def test_decrypt_invalid_data_fails(self) -> None:
        """無効なデータの復号化は失敗すること"""
        encryptor = get_session_encryption()

        with pytest.raises(Exception):
            encryptor.decrypt("invalid-encrypted-data")

    def test_encrypt_empty_dict(self) -> None:
        """空の辞書を暗号化できること"""
        encryptor = get_session_encryption()
        data: Dict[str, Any] = {}
        encrypted = encryptor.encrypt(data)
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == data

    def test_encrypt_japanese_characters(self) -> None:
        """日本語を含むデータを暗号化できること"""
        encryptor = get_session_encryption()
        data: Dict[str, str] = {"name": "テストユーザー", "message": "こんにちは世界"}
        encrypted = encryptor.encrypt(data)
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == data

    def test_encrypt_nested_data(self) -> None:
        """ネストしたデータを暗号化できること"""
        encryptor = get_session_encryption()
        data: Dict[str, Any] = {
            "user": {
                "id": "123",
                "profile": {
                    "name": "Test User",
                    "roles": ["admin", "user"],
                    "settings": {"theme": "dark", "language": "ja"},
                },
            },
            "session_data": {
                "created_at": "2024-01-01T00:00:00Z",
                "last_activity": "2024-01-02T12:00:00Z",
            },
        }
        encrypted = encryptor.encrypt(data)
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == data

    def test_encrypt_special_characters(self) -> None:
        """特殊文字を含むデータを暗号化できること"""
        encryptor = get_session_encryption()
        data: Dict[str, str] = {
            "password": "P@ssw0rd!#$%",
            "symbols": "~`!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/",
            "unicode": "é ñ ü ö ä",
        }
        encrypted = encryptor.encrypt(data)
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == data

    def test_encrypt_large_data(self) -> None:
        """大きなデータを暗号化できること"""
        encryptor = get_session_encryption()
        # 大きなリストを含むデータ
        data: Dict[str, Any] = {
            "large_list": list(range(1000)),
            "large_dict": {f"key_{i}": f"value_{i}" for i in range(100)},
        }
        encrypted = encryptor.encrypt(data)
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == data
