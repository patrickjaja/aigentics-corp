"""
API Package

Combines all API routers for the AI Offer Agent.
"""

from fastapi import APIRouter

from .conversations import router as conversations_router
from .offers import router as offers_router
from .customers import router as customers_router
from .admin import router as admin_router
from .health import router as health_router


# Create main API router
api_router = APIRouter(prefix="/v1")

# Include all sub-routers
api_router.include_router(conversations_router)
api_router.include_router(offers_router)
api_router.include_router(customers_router)
api_router.include_router(admin_router)

# Create health router (not under /v1 prefix)
health_api_router = APIRouter()
health_api_router.include_router(health_router)


__all__ = [
    "api_router",
    "health_api_router",
    "conversations_router",
    "offers_router",
    "customers_router",
    "admin_router",
    "health_router"
]
