from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    from core import get_settings
except ImportError:
    from core.config import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
