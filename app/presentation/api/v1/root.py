from fastapi import APIRouter, Request, Response

router = APIRouter()


@router.get("/")
async def read_root(request: Request, response: Response) -> dict[str, str]:
    """
    ルートエンドポイント
    """
    return {"message": "Hello World"}
