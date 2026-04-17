from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings


app = FastAPI(
    title="File Sharing Web Application API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.include_router(router)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "service": "backend",
        "environment": settings.app_env,
        "status": "ok",
    }
