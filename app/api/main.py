from fastapi import FastAPI

from app.core.config import get_settings
from app.api.routes import devices, auth

settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)


@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


app.include_router(devices.router, prefix="/api")
app.include_router(auth.router, prefix="/api")