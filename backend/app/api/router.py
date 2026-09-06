"""Router composition. Route order matters: static segments before path params."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, businesses, images, items, taxonomy
from app.api.v1.admin import businesses as admin_businesses
from app.api.v1.admin import stats as admin_stats
from app.api.v1.admin import taxonomy as admin_taxonomy
from app.api.v1.admin import users as admin_users

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(taxonomy.router)

# Admin routes are registered before the owner/public business routes so that
# "/api/admin/businesses/..." is never captured by "/api/businesses/{slug}".
api_router.include_router(admin_businesses.router)
api_router.include_router(admin_taxonomy.router)
api_router.include_router(admin_stats.router)
api_router.include_router(admin_users.router)

api_router.include_router(businesses.owner_router)
api_router.include_router(images.router)
api_router.include_router(items.router)
api_router.include_router(businesses.public_router)
api_router.include_router(items.public_router)

__all__ = ["api_router"]
