"""Router composition. Route order matters: static segments before path params."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    articles,
    auth,
    businesses,
    feedback,
    images,
    items,
    orders,
    service_requests,
    talent,
    talent_images,
    taxonomy,
    testimonials,
)
from app.api.v1.admin import articles as admin_articles
from app.api.v1.admin import businesses as admin_businesses
from app.api.v1.admin import feedback as admin_feedback
from app.api.v1.admin import stats as admin_stats
from app.api.v1.admin import talent as admin_talent
from app.api.v1.admin import taxonomy as admin_taxonomy
from app.api.v1.admin import users as admin_users

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(taxonomy.router)

# Admin routes are registered before the owner/public business routes so that
# "/api/admin/businesses/..." is never captured by "/api/businesses/{slug}".
api_router.include_router(admin_articles.router)
api_router.include_router(admin_businesses.router)
api_router.include_router(admin_feedback.router)
api_router.include_router(admin_talent.router)
api_router.include_router(admin_taxonomy.router)
api_router.include_router(admin_stats.router)
api_router.include_router(admin_users.router)
api_router.include_router(testimonials.admin_router)

api_router.include_router(feedback.router)
api_router.include_router(analytics.owner_router)
# Owner testimonial routes before the public business routes, so
# "/api/businesses/{business_id}/testimonials" is never captured by
# "/api/businesses/{slug}".
api_router.include_router(testimonials.owner_router)
api_router.include_router(orders.owner_router)
api_router.include_router(businesses.owner_router)
api_router.include_router(images.router)
api_router.include_router(items.router)
# Likewise "/api/my/talent/..." before "/api/talent/{slug}".
api_router.include_router(service_requests.owner_router)
api_router.include_router(talent.owner_router)
api_router.include_router(talent_images.router)
api_router.include_router(testimonials.public_router)
api_router.include_router(orders.public_router)
api_router.include_router(businesses.public_router)
api_router.include_router(articles.router)
api_router.include_router(items.public_router)
api_router.include_router(service_requests.public_router)
api_router.include_router(talent.public_router)

__all__ = ["api_router"]
