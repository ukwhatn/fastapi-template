from fastapi import APIRouter

from api import v1, system

api_router = APIRouter()
api_router.include_router(v1.router, prefix="/v1")
api_router.include_router(system.router, prefix="/system")
