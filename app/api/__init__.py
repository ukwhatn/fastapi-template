from fastapi import APIRouter

from api import v1, system
from core import get_settings

settings = get_settings()

api_router = APIRouter()
api_router.include_router(v1.router, prefix=settings.API_V1_STR)
api_router.include_router(system.router, prefix=settings.SYSTEM_STR)
