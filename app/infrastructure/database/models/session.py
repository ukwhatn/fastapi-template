from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from .base import Base, TimeStampMixin


class Session(Base, TimeStampMixin):
    """
    セッションモデル

    Attributes:
        session_id: セッションID（主キー）
        data: 暗号化されたセッションデータ（JSON）
        expires_at: セッション有効期限
        fingerprint: セッションフィンガープリント（User-Agent + IPのハッシュ）
        csrf_token: CSRFトークン
    """

    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)  # 暗号化されたJSON
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA256ハッシュ
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)

    def __repr__(self) -> str:
        return f"<Session(session_id={self.session_id}, expires_at={self.expires_at})>"
