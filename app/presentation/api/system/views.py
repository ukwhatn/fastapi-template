from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from utils import get_templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    インデックスページ（テンプレートが有効な場合）
    """
    templates = get_templates(request)
    if templates is None:
        raise HTTPException(
            status_code=404,
            detail="Templates not enabled. Add files to app/templates/ directory.",
        )

    return templates.TemplateResponse(
        "index.html", {"request": request, "title": "FastAPI Template"}
    )
