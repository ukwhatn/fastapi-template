from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    DB接続のためのデペンデンシー
    yield構文でセッションをコンテキストマネージャとして提供
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()