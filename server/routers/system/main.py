from fastapi import APIRouter

from .healthcheck import main as healthcheck_router

# define router
router = APIRouter()

# add routers
router.include_router(
    healthcheck_router.router,
    prefix='/healthcheck',
)
