from typing import Dict
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def healthcheck() -> Dict[str, str]:
    """
    ヘルスチェックエンドポイント
    """
    return {"status": "ok"}
