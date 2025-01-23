from contextlib import contextmanager

from .connection import SessionLocal


def db_context():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


get_db = contextmanager(db_context)
