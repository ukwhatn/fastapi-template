from fastapi import APIRouter
from fastapi import Request, Response, Depends
from sqlalchemy.orm import Session

from db.session import get_db

# define router
router = APIRouter(
    tags=["template"],
)


# define route
@router.get("/")
async def read_root(request: Request, response: Response, db: Session = Depends(get_db)):
    return {"message": "Hello World"}
