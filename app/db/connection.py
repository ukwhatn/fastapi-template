from contextlib import contextmanager

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


@contextmanager
def db_session():
    """
    with句で使用できるデータベースセッションのコンテキストマネージャ
    使用例:
    with db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
