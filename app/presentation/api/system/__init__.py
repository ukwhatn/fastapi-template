from fastapi import APIRouter

from . import healthcheck, views

router = APIRouter()
router.include_router(healthcheck.router, prefix="/healthcheck", tags=["system"])
router.include_router(views.router, prefix="/views", tags=["views"])
