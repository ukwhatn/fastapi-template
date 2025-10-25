from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# データベース接続設定
if settings.has_database:
    engine = create_engine(
        settings.database_uri,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info(f"Database connection established")

    if settings.is_supabase:
        logger.info("Using Supabase as database provider")
else:
    engine = None
    SessionLocal = None
    logger.warning("DATABASE_URL not set. Database functionality disabled.")


def get_db():
    """
    DB接続のためのデペンデンシー
    yield構文でセッションをコンテキストマネージャとして提供
    """
    if not SessionLocal:
        raise RuntimeError("Database not configured. Set DATABASE_URL environment variable.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
