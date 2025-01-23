from fastapi import APIRouter, Depends
from fastapi import Request, Response
from sqlalchemy import text

from db.package.session import db_context

# define router
router = APIRouter()


# define route
@router.get("/")
async def healthcheck(request: Request, response: Response, db=Depends(db_context)):
    # dbへのアクセスをテスト
    db.execute(text("SELECT 1"))

    # redisへのアクセスをテスト
    # middlewareで実施しているため、ここでは不要

    # response
    return {"status": "ok"}
