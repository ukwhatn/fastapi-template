from fastapi import APIRouter

from app.api import v1, system
from app.core import get_settings

settings = get_settings()

api_router = APIRouter()

# APIバージョン別ルーターを登録
api_router.include_router(v1.router, prefix=settings.API_V1_STR)

# システムルーターを登録
api_router.include_router(system.router, prefix=settings.SYSTEM_STR)