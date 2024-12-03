from contextlib import contextmanager

from .connection import SessionLocal


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_context = contextmanager(db_session)
