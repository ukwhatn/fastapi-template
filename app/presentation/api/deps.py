from dataclasses import dataclass
from typing import Any, Generator

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from starlette.status import HTTP_403_FORBIDDEN

from ...core.config import get_settings
from ...infrastructure.database import get_db
from ...utils.schemas import SessionSchema


@dataclass
class DBWithSession:
    db: Session
    session: SessionSchema


def get_session(request: Request) -> SessionSchema:
    """
    セッションデータを取得するdependency
    """
    session = request.state.session
    # すでにSessionSchemaの場合はそのまま返す
    if isinstance(session, SessionSchema):
        return session
    # dictの場合はSessionSchemaに変換
    session_data: dict[str, Any] = session if session is not None else {}
    return SessionSchema(data=session_data)


def get_db_with_session(
    db: Session = Depends(get_db),
    session: SessionSchema = Depends(get_session),
) -> Generator[DBWithSession, None, None]:
    """
    DBとセッションの両方を取得するdependency

    Note: db.close()は不要。get_db()が既にセッションのクローズを管理している
    """
    yield DBWithSession(db=db, session=session)


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
