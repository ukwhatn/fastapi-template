from contextlib import contextmanager

from .connection import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_context = contextmanager(get_db)
