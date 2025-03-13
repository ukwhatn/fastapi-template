from fastapi import APIRouter

from app.api.v1 import items, root

router = APIRouter()

# ルーターを登録
router.include_router(root.router, tags=["root"])
router.include_router(items.router, prefix="/items", tags=["items"])
