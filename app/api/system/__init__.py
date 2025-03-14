from fastapi import APIRouter

from api.system import healthcheck

router = APIRouter()
router.include_router(healthcheck.router, prefix="/healthcheck", tags=["system"])
