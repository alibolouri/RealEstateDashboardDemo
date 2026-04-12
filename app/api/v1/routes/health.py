from fastapi import APIRouter

from app.core.config import get_settings


router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }
