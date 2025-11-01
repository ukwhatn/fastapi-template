"""セッション管理ミドルウェア"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.core.config import get_settings
from app.infrastructure.database import get_db
from app.infrastructure.repositories.session_repository import SessionService

settings = get_settings()


async def session_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    セッション管理ミドルウェア

    DATABASE_URLが設定されている場合のみ、RDBベースのセッション管理を有効化

    Args:
        request: HTTPリクエスト
        call_next: 次のミドルウェア/エンドポイント

    Returns:
        HTTPレスポンス
    """
    if settings.has_database:
        db_gen = get_db()
        db = next(db_gen)
        try:
            session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
            if session_id:
                service = SessionService(db)
                user_agent = request.headers.get("User-Agent")
                client_ip_headers = ["CF-Connecting-IP", "X-Forwarded-For"]
                client_ip = None
                for header in client_ip_headers:
                    client_ip = request.headers.get(header)
                    if client_ip:
                        break
                if not client_ip:
                    client_ip = request.client.host if request.client else None

                session_data = service.get_session(session_id, user_agent, client_ip)

                request.state.session = session_data or {}
                request.state.session_id = session_id
                request.state.client_ip = client_ip
                request.state.user_agent = user_agent
            else:
                request.state.session = {}

            response = await call_next(request)

            # セッションデータの永続化は各エンドポイントで明示的に実施
            # ミドルウェアでの自動保存は行わない（パフォーマンス対策）

            return response
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    else:
        request.state.session = None
        return await call_next(request)
