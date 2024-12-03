from datetime import datetime

from sqlalchemy import Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from .connection import Base


class TemplateTable(Base):
    __tablename__ = "template_tables"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=text("now()")
    )
