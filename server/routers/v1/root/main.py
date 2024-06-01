from fastapi import APIRouter
from fastapi import Request, Response

# define router
router = APIRouter()


# define route
@router.get("/")
async def read_root(request: Request, response: Response):
    print("test")
    return {"message": "Hello World"}
