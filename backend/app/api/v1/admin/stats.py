"""Platform statistics and the administrator's user list."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.serializers import admin_user
from app.core.dependencies import AdminUser, DbSession
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus, UserRole
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository
from app.repositories.user import UserRepository
from app.schemas.common import PageMeta, PaginatedResponse, StatsResponse
from app.schemas.moderation import AdminUserOut

router = APIRouter(prefix="/admin", tags=["admin-stats"])


@router.get("/stats", response_model=StatsResponse)
def platform_stats(db: DbSession, admin: AdminUser) -> StatsResponse:
    counts = BusinessRepository(db).count_by_status()
    talent_counts = TalentRepository(db).count_by_status()
    users = UserRepository(db)
    total_items = int(
        db.execute(select(func.count()).select_from(BusinessItem)).scalar_one()
    )

    return StatsResponse(
        total_businesses=sum(counts.values()),
        pending_businesses=counts.get(BusinessStatus.PENDING_REVIEW, 0),
        approved_businesses=counts.get(BusinessStatus.APPROVED, 0),
        rejected_businesses=counts.get(BusinessStatus.REJECTED, 0),
        suspended_businesses=counts.get(BusinessStatus.SUSPENDED, 0),
        draft_businesses=counts.get(BusinessStatus.DRAFT, 0),
        total_users=users.count(),
        total_admins=users.count_by_role(UserRole.ADMIN),
        total_items=total_items,
        total_talents=sum(talent_counts.values()),
        pending_talents=talent_counts.get(BusinessStatus.PENDING_REVIEW, 0),
        approved_talents=talent_counts.get(BusinessStatus.APPROVED, 0),
    )


@router.get("/users", response_model=PaginatedResponse[AdminUserOut])
def list_users(
    db: DbSession,
    admin: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PaginatedResponse[AdminUserOut]:
    users, total = UserRepository(db).list_users(
        limit=page_size, offset=(page - 1) * page_size
    )

    counts: dict[uuid.UUID, int] = {
        row[0]: row[1]
        for row in db.execute(
            select(Business.owner_id, func.count()).group_by(Business.owner_id)
        ).all()
    }

    page_size = max(page_size, 1)
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse[AdminUserOut](
        items=[admin_user(user, business_count=counts.get(user.id, 0)) for user in users],
        meta=PageMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )
