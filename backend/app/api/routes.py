from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.users import router as users_router

router = APIRouter(prefix="/api")
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(users_router, prefix="/users", tags=["users"])
