from fastapi import APIRouter

from . import system, v1

api_router = APIRouter(prefix="/api")
api_router.include_router(v1.router, prefix="/v1")
api_router.include_router(system.router, prefix="/system")
