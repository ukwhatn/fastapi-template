from fastapi import APIRouter

from app.api.system import healthcheck

router = APIRouter()

# ルーターを登録
router.include_router(healthcheck.router, prefix="/healthcheck", tags=["system"])
