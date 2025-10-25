from dataclasses import dataclass
from typing import Generator

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from starlette.status import HTTP_403_FORBIDDEN

from core.config import get_settings
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


# API認証用のヘッダーハンドラーを作成
api_key_header = APIKeyHeader(
    name="Authorization", scheme_name="Bearer", auto_error=False
)


def get_api_key(
    api_key_header: str = Security(api_key_header),
) -> str:
    """
    APIキー認証のdependency
    Authorizationヘッダーに'Bearer {api_key}'形式で指定されたAPIキーを検証

    - Authorization: Bearer your-api-key-here
    """
    settings = get_settings()

    if not api_key_header:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Authorization header missing"
        )

    # Bearerプレフィックスの処理
    scheme, _, api_key = api_key_header.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Authorization header must start with 'Bearer'",
        )

    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API key")

    return api_key
