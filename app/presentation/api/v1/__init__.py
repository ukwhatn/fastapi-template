from fastapi import APIRouter

from app.presentation.api.v1 import root

router = APIRouter()
router.include_router(root.router, tags=["root"])
