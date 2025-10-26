"""
セッション管理ヘルパー

FastAPIのRequestとResponseからセッションを操作するための便利な関数
"""

from typing import Any, Optional
from fastapi import Request, Response
from sqlalchemy.orm import Session as DBSession

from ..infrastructure.repositories.session_repository import SessionService
from ..core.config import get_settings


def get_client_ip(request: Request) -> Optional[str]:
    """
    クライアントIPアドレスを取得

    X-Forwarded-Forヘッダーまたはclient.hostから取得

    Args:
        request: FastAPI Request

    Returns:
        クライアントIPアドレス
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-Forには複数のIPが含まれる可能性があるため、最初のものを使用
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> Optional[str]:
    """
    User-Agentヘッダーを取得

    Args:
        request: FastAPI Request

    Returns:
        User-Agentヘッダー
    """
    return request.headers.get("User-Agent")


def create_session(
    db: DBSession,
    response: Response,
    request: Request,
    data: dict[str, Any],
) -> tuple[str, str]:
    """
    新しいセッションを作成してCookieに設定

    Args:
        db: DBセッション
        response: FastAPI Response
        request: FastAPI Request
        data: セッションデータ

    Returns:
        (session_id, csrf_token) のタプル
    """
    settings = get_settings()
    service = SessionService(db)
    user_agent = get_user_agent(request)
    client_ip = get_client_ip(request)

    session_id, csrf_token = service.create_session(data, user_agent, client_ip)

    # Cookieに設定
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=settings.is_production,  # 本番環境ではHTTPSのみ
        samesite="lax",
    )

    return session_id, csrf_token


def get_session_data(
    db: DBSession,
    request: Request,
    verify_csrf: bool = False,
    csrf_token: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    セッションデータを取得

    Args:
        db: DBセッション
        request: FastAPI Request
        verify_csrf: CSRFトークンを検証するか
        csrf_token: CSRFトークン（verify_csrf=Trueの場合）

    Returns:
        セッションデータ、存在しない場合はNone
    """
    settings = get_settings()
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_id:
        return None

    service = SessionService(db)
    user_agent = get_user_agent(request)
    client_ip = get_client_ip(request)

    return service.get_session(
        session_id, user_agent, client_ip, verify_csrf, csrf_token
    )


def update_session_data(
    db: DBSession,
    request: Request,
    data: dict[str, Any],
) -> bool:
    """
    セッションデータを更新

    Args:
        db: DBセッション
        request: FastAPI Request
        data: 新しいセッションデータ

    Returns:
        更新成功時True
    """
    settings = get_settings()
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_id:
        return False

    service = SessionService(db)
    user_agent = get_user_agent(request)
    client_ip = get_client_ip(request)

    return service.update_session(session_id, data, user_agent, client_ip)


def delete_session(
    db: DBSession,
    request: Request,
    response: Response,
) -> bool:
    """
    セッションを削除してCookieをクリア

    Args:
        db: DBセッション
        request: FastAPI Request
        response: FastAPI Response

    Returns:
        削除成功時True
    """
    settings = get_settings()
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_id:
        return False

    service = SessionService(db)
    result = service.delete_session(session_id)

    # Cookieを削除
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME)

    return result


def regenerate_session_id(
    db: DBSession,
    request: Request,
    response: Response,
) -> Optional[tuple[str, str]]:
    """
    セッションIDを再生成（ログイン時などに使用）

    Args:
        db: DBセッション
        request: FastAPI Request
        response: FastAPI Response

    Returns:
        (新しいsession_id, 新しいcsrf_token) のタプル、失敗時はNone
    """
    settings = get_settings()
    old_session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not old_session_id:
        return None

    service = SessionService(db)
    user_agent = get_user_agent(request)
    client_ip = get_client_ip(request)

    result = service.regenerate_session_id(old_session_id, user_agent, client_ip)
    if not result:
        return None

    new_session_id, new_csrf_token = result

    # Cookieを更新
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=new_session_id,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )

    return new_session_id, new_csrf_token


def get_csrf_token(db: DBSession, request: Request) -> Optional[str]:
    """
    CSRFトークンを取得

    Args:
        db: DBセッション
        request: FastAPI Request

    Returns:
        CSRFトークン、セッションが存在しない場合はNone
    """
    settings = get_settings()
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_id:
        return None

    service = SessionService(db)
    return service.get_csrf_token(session_id)
