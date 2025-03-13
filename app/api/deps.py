from typing import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.utils import SessionCrud, SessionSchema


def get_session(request: Request) -> SessionSchema:
    """
    セッションデータを取得するデペンデンシー
    """
    return request.state.session


def get_db_with_session(
    db: Session = Depends(get_db),
    session: SessionSchema = Depends(get_session),
) -> Generator[Session, None, None]:
    """
    DBとセッションの両方を取得するデペンデンシー
    """
    try:
        yield db
    finally:
        pass