from fastapi import APIRouter, Request, Response

router = APIRouter()


@router.get("/")
async def read_root(request: Request, response: Response):
    """
    ルートエンドポイント
    """
    return {"message": "Hello World"}
