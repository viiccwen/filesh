from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.v1.share_access import router as share_access_router
from app.core.config import settings

app = FastAPI(
    title="File Sharing Web Application API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(share_access_router)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "service": "backend",
        "environment": settings.app_env,
        "status": "ok",
    }
