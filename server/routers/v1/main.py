from fastapi import APIRouter

from .root import main as root_router

# define router
router = APIRouter()

# add routers
router.include_router(
    root_router.router
)
