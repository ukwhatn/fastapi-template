"""
セキュリティ関連のヘルパーモジュール

セッション暗号化、CSRF保護、セッションフィンガープリント生成など
"""

import hashlib
import secrets
import json
import logging
from typing import Any, Optional
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SessionEncryption:
    """
    セッションデータの暗号化/復号化

    Fernet (対称暗号化) を使用してセッションデータを安全に保存
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Args:
            encryption_key: 暗号化キー（Noneの場合は設定から取得）
        """
        # 依存性注入: テスト時は明示的にキーを渡せる
        if encryption_key is None:
            settings = get_settings()
            encryption_key = settings.SESSION_ENCRYPTION_KEY

        self.encryption_key = encryption_key
        if self.encryption_key:
            try:
                self.cipher = Fernet(self.encryption_key.encode())
                self.enabled = True
                logger.info("Session encryption enabled")
            except Exception as e:
                logger.error(f"Failed to initialize session encryption: {e}")
                self.cipher = None
                self.enabled = False
        else:
            self.cipher = None
            self.enabled = False
            logger.warning("Session encryption disabled (SESSION_ENCRYPTION_KEY not set)")

    def encrypt(self, data: dict[str, Any]) -> str:
        """
        セッションデータを暗号化

        Args:
            data: 暗号化するデータ（dict）

        Returns:
            暗号化されたデータ（Base64エンコードされた文字列）
        """
        if not self.enabled or not self.cipher:
            # 暗号化無効時はJSON文字列をそのまま返す（非推奨）
            logger.warning("Storing session data without encryption")
            return json.dumps(data, ensure_ascii=False)

        try:
            # JSONシリアライズ → バイト列に変換 → 暗号化
            json_str = json.dumps(data, ensure_ascii=False)
            encrypted = self.cipher.encrypt(json_str.encode("utf-8"))
            return encrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to encrypt session data: {e}")
            raise ValueError("Session encryption failed")

    def decrypt(self, encrypted_data: str) -> dict[str, Any]:
        """
        暗号化されたセッションデータを復号化

        Args:
            encrypted_data: 暗号化されたデータ（Base64文字列）

        Returns:
            復号化されたデータ（dict）

        Raises:
            ValueError: 復号化に失敗した場合
        """
        if not self.enabled or not self.cipher:
            # 暗号化無効時はJSONパース
            try:
                return json.loads(encrypted_data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse session data: {e}")
                raise ValueError("Invalid session data")

        try:
            # 復号化 → バイト列からデコード → JSONパース
            decrypted = self.cipher.decrypt(encrypted_data.encode("utf-8"))
            json_str = decrypted.decode("utf-8")
            return json.loads(json_str)
        except InvalidToken:
            logger.error("Invalid encryption token for session data")
            raise ValueError("Invalid or corrupted session data")
        except Exception as e:
            logger.error(f"Failed to decrypt session data: {e}")
            raise ValueError("Session decryption failed")


def generate_csrf_token() -> str:
    """
    CSRFトークンを生成

    Returns:
        ランダムな64文字のHEX文字列
    """
    return secrets.token_hex(32)


def generate_session_id() -> str:
    """
    セッションIDを生成

    Returns:
        ランダムな64文字のHEX文字列
    """
    return secrets.token_hex(32)


def generate_fingerprint(user_agent: Optional[str], client_ip: Optional[str]) -> str:
    """
    セッションフィンガープリントを生成

    User-AgentとクライアントIPのSHA256ハッシュを生成
    セッション固定攻撃への対策として使用

    Args:
        user_agent: User-Agentヘッダー
        client_ip: クライアントIPアドレス

    Returns:
        SHA256ハッシュ（64文字のHEX文字列）
    """
    ua = user_agent or "unknown"
    ip = client_ip or "unknown"
    fingerprint_str = f"{ua}|{ip}"
    return hashlib.sha256(fingerprint_str.encode("utf-8")).hexdigest()


def verify_fingerprint(
    stored_fingerprint: str, user_agent: Optional[str], client_ip: Optional[str]
) -> bool:
    """
    セッションフィンガープリントを検証

    Args:
        stored_fingerprint: 保存されているフィンガープリント
        user_agent: 現在のUser-Agentヘッダー
        client_ip: 現在のクライアントIPアドレス

    Returns:
        フィンガープリントが一致する場合True
    """
    current_fingerprint = generate_fingerprint(user_agent, client_ip)
    return secrets.compare_digest(stored_fingerprint, current_fingerprint)


# シングルトンインスタンス
_session_encryption = None


def get_session_encryption() -> SessionEncryption:
    """
    SessionEncryptionのシングルトンインスタンスを取得

    Returns:
        SessionEncryptionインスタンス
    """
    global _session_encryption
    if _session_encryption is None:
        _session_encryption = SessionEncryption()
    return _session_encryption
