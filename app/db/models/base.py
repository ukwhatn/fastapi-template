from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, declarative_base
from sqlalchemy.sql import text

Base = declarative_base()


class TimeStampMixin:
    """
    タイムスタンプMixin
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()")
    )


class BaseModel(Base, TimeStampMixin):
    """
    ベースモデル
    全てのモデルで継承して使用
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
