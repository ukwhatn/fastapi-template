from dataclasses import dataclass
from typing import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from db import get_db
from utils import SessionSchema


@dataclass
class DBWithSession:
    db: Session
    session: SessionSchema


def get_session(request: Request) -> SessionSchema:
    """
    セッションデータを取得するdependency
    """
    return request.state.session


def get_db_with_session(
    db: Session = Depends(get_db),
    session: SessionSchema = Depends(get_session),
) -> Generator[DBWithSession, None, None]:
    """
    DBとセッションの両方を取得するdependency
    """
    try:
        yield DBWithSession(db=db, session=session)
    finally:
        db.close()
