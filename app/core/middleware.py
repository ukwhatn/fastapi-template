from typing import Callable

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core import get_settings

settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    セキュリティヘッダーを追加するミドルウェア
    """
    
    def __init__(
            self,
            app: FastAPI,
    ) -> None:
        super().__init__(app)
    
    async def dispatch(
            self, request: Request, call_next: Callable
    ) -> Response:
        response = await call_next(request)
        
        if settings.SECURITY_HEADERS:
            # CSP (Content-Security-Policy)
            response.headers["Content-Security-Policy"] = settings.CSP_POLICY
            
            # XSS Protection
            response.headers["X-XSS-Protection"] = "1; mode=block"
            
            # Frame Options
            response.headers["X-Frame-Options"] = "DENY"
            
            # Content Type Options
            response.headers["X-Content-Type-Options"] = "nosniff"
            
            # Referrer Policy
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            
            # HSTS (HTTP Strict Transport Security)
            if settings.is_production:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            
            # Feature Policy
            response.headers["Permissions-Policy"] = (
                "camera=(), microphone=(), geolocation=(), interest-cohort=()"
            )
        
        return response