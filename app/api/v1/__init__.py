from fastapi import APIRouter

from api.v1 import items, root

router = APIRouter()
router.include_router(root.router, tags=["root"])
router.include_router(items.router, prefix="/items", tags=["items"])
