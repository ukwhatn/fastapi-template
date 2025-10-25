from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def healthcheck():
    """
    ヘルスチェックエンドポイント
    """
    return {"status": "ok"}
