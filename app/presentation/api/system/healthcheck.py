from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def healthcheck() -> dict[str, str]:
    """
    ヘルスチェックエンドポイント
    """
    return {"status": "ok"}
