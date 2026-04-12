from fastapi import APIRouter

from app.api.v1.routes import chat, health, leads, properties, realtors


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(properties.router, prefix="/api/v1")
api_router.include_router(chat.router, prefix="/api/v1")
api_router.include_router(leads.router, prefix="/api/v1")
api_router.include_router(realtors.router, prefix="/api/v1")
