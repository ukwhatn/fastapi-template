"""
セッション管理サービス

RDBベースのセッション管理を提供
- 暗号化されたセッションデータの保存/取得
- CSRF保護
- セッション固定攻撃への対策（フィンガープリント検証）
- 期限切れセッションの自動削除
"""

import logging
from typing import Any, Optional, cast
from datetime import datetime, timedelta
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import delete

from ..database.models.session import Session
from ...core.config import get_settings
from ..security.encryption import (
    SessionEncryption,
    get_session_encryption,
    generate_session_id,
    generate_csrf_token,
    generate_fingerprint,
    verify_fingerprint,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class SessionService:
    """
    セッション管理サービス
    """

    def __init__(self, db: DBSession, encryption: Optional["SessionEncryption"] = None):
        """
        Args:
            db: DBセッション
            encryption: 暗号化インスタンス（Noneの場合はデフォルト取得）
        """
        self.db = db
        # 依存性注入: テスト時はモックインスタンスを渡せる
        self.encryption = (
            encryption if encryption is not None else get_session_encryption()
        )

    def create_session(
        self,
        data: dict[str, Any],
        user_agent: Optional[str] = None,
        client_ip: Optional[str] = None,
        expire_seconds: Optional[int] = None,
    ) -> tuple[str, str]:
        """
        新しいセッションを作成

        Args:
            data: セッションデータ
            user_agent: User-Agentヘッダー
            client_ip: クライアントIPアドレス
            expire_seconds: 有効期限（秒）、Noneの場合は設定値を使用

        Returns:
            (session_id, csrf_token) のタプル
        """
        session_id = generate_session_id()
        csrf_token = generate_csrf_token()
        fingerprint = generate_fingerprint(user_agent, client_ip)

        # 有効期限計算
        if expire_seconds is None:
            expire_seconds = settings.SESSION_EXPIRE
        expires_at = datetime.now() + timedelta(seconds=expire_seconds)

        # データ暗号化
        encrypted_data = self.encryption.encrypt(data)

        # セッションレコード作成
        session = Session(
            session_id=session_id,
            data=encrypted_data,
            expires_at=expires_at,
            fingerprint=fingerprint,
            csrf_token=csrf_token,
        )

        self.db.add(session)
        self.db.commit()

        logger.info(f"Session created: {session_id}")
        return session_id, csrf_token

    def get_session(
        self,
        session_id: str,
        user_agent: Optional[str] = None,
        client_ip: Optional[str] = None,
        verify_csrf: bool = False,
        csrf_token: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        セッションを取得

        Args:
            session_id: セッションID
            user_agent: User-Agentヘッダー（フィンガープリント検証用）
            client_ip: クライアントIPアドレス（フィンガープリント検証用）
            verify_csrf: CSRFトークンを検証するか
            csrf_token: CSRFトークン（verify_csrf=Trueの場合必須）

        Returns:
            セッションデータ、存在しないまたは無効な場合はNone
        """
        session = (
            self.db.query(Session).filter(Session.session_id == session_id).first()
        )

        if not session:
            logger.debug(f"Session not found: {session_id}")
            return None

        # 有効期限チェック
        if session.expires_at < datetime.now():
            logger.info(f"Session expired: {session_id}")
            self.delete_session(session_id)
            return None

        # フィンガープリント検証
        if not verify_fingerprint(session.fingerprint, user_agent, client_ip):
            logger.warning(f"Session fingerprint mismatch: {session_id}")
            # セキュリティ上、セッションを削除
            self.delete_session(session_id)
            return None

        # CSRF検証
        if verify_csrf:
            if not csrf_token:
                logger.warning(f"CSRF token not provided for session: {session_id}")
                return None
            if csrf_token != session.csrf_token:
                logger.warning(f"CSRF token mismatch for session: {session_id}")
                return None

        # データ復号化
        try:
            data = self.encryption.decrypt(session.data)
            return data
        except ValueError as e:
            logger.error(f"Failed to decrypt session data for {session_id}: {e}")
            # 復号化失敗時はセッションを削除
            self.delete_session(session_id)
            return None

    def update_session(
        self,
        session_id: str,
        data: dict[str, Any],
        user_agent: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> bool:
        """
        セッションデータを更新

        Args:
            session_id: セッションID
            data: 新しいセッションデータ
            user_agent: User-Agentヘッダー（フィンガープリント検証用）
            client_ip: クライアントIPアドレス（フィンガープリント検証用）

        Returns:
            更新成功時True、失敗時False
        """
        session = (
            self.db.query(Session).filter(Session.session_id == session_id).first()
        )

        if not session:
            logger.debug(f"Session not found for update: {session_id}")
            return False

        # 有効期限チェック
        if session.expires_at < datetime.now():
            logger.info(f"Cannot update expired session: {session_id}")
            self.delete_session(session_id)
            return False

        # フィンガープリント検証
        if not verify_fingerprint(session.fingerprint, user_agent, client_ip):
            logger.warning(
                f"Cannot update session with fingerprint mismatch: {session_id}"
            )
            self.delete_session(session_id)
            return False

        # データ暗号化して更新
        try:
            encrypted_data = self.encryption.encrypt(data)
            session.data = encrypted_data
            session.updated_at = datetime.now()
            self.db.commit()
            logger.info(f"Session updated: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            self.db.rollback()
            return False

    def delete_session(self, session_id: str) -> bool:
        """
        セッションを削除

        Args:
            session_id: セッションID

        Returns:
            削除成功時True、失敗時False
        """
        try:
            result = self.db.execute(
                delete(Session).where(Session.session_id == session_id)
            )
            self.db.commit()
            rowcount = cast(int, getattr(result, "rowcount", 0))
            deleted = rowcount > 0
            if deleted:
                logger.info(f"Session deleted: {session_id}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            self.db.rollback()
            return False

    def cleanup_expired_sessions(self) -> int:
        """
        期限切れセッションをクリーンアップ

        Returns:
            削除されたセッション数
        """
        try:
            result = self.db.execute(
                delete(Session).where(Session.expires_at < datetime.now())
            )
            self.db.commit()
            count = cast(int, getattr(result, "rowcount", 0))
            if count > 0:
                logger.info(f"Cleaned up {count} expired sessions")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            self.db.rollback()
            return 0

    def regenerate_session_id(
        self,
        old_session_id: str,
        user_agent: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> Optional[tuple[str, str]]:
        """
        セッションIDを再生成（セッション固定攻撃対策）

        ログイン成功時などに呼び出して、セッションIDを新しいものに変更する

        Args:
            old_session_id: 古いセッションID
            user_agent: User-Agentヘッダー
            client_ip: クライアントIPアドレス

        Returns:
            (新しいsession_id, 新しいcsrf_token) のタプル、失敗時はNone
        """
        # 既存セッション取得
        data = self.get_session(old_session_id, user_agent, client_ip)
        if data is None:
            logger.warning(f"Cannot regenerate non-existent session: {old_session_id}")
            return None

        # 古いセッション削除
        self.delete_session(old_session_id)

        # 新しいセッション作成
        new_session_id, new_csrf_token = self.create_session(
            data, user_agent, client_ip
        )

        logger.info(f"Session ID regenerated: {old_session_id} -> {new_session_id}")
        return new_session_id, new_csrf_token

    def get_csrf_token(self, session_id: str) -> Optional[str]:
        """
        セッションのCSRFトークンを取得

        Args:
            session_id: セッションID

        Returns:
            CSRFトークン、セッションが存在しない場合はNone
        """
        session = (
            self.db.query(Session).filter(Session.session_id == session_id).first()
        )
        return session.csrf_token if session else None
