from datetime import datetime, UTC

from sqlalchemy import Column, Integer, String, DateTime

from .connection import Base


class TemplateModel(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC))
    deleted_at = Column(DateTime, nullable=True)
