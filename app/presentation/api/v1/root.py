from typing import Dict
from fastapi import APIRouter, Request, Response

router = APIRouter()


@router.get("/")
async def read_root(request: Request, response: Response) -> Dict[str, str]:
    """
    ルートエンドポイント
    """
    return {"message": "Hello World"}
