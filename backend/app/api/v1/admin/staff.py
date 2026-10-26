"""Staff accounts: the manager invites, re-roles, disables and re-issues.

Manager-only by ``app/core/permissions.py``. An invitation is an account
created with a role and a generated password, shown once and relayed by the
manager on WhatsApp -- the same path an owner's password takes, because the
site sends no email or SMS. Two guards keep the admin area reachable: a
manager cannot change or disable their own account, and the last active
manager cannot be demoted or disabled.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from sqlalchemy import func, select

from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.enums import StaffRole, UserRole
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.staff import StaffInviteIn, StaffOut, StaffPasswordOut, StaffUpdateIn
from app.services.auth import AuthService

router = APIRouter(prefix="/admin", tags=["admin-staff"])


def _load(db: DbSession, user_id: uuid.UUID) -> User:
    user = UserRepository(db).get(user_id)
    if user is None or user.role is not UserRole.ADMIN:
        raise NotFoundError("staff.not_found")
    return user


def _active_managers(db: DbSession) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(User)
            .where(
                User.role == UserRole.ADMIN,
                User.staff_role == StaffRole.MANAGER,
                User.is_active.is_(True),
            )
        ).scalar_one()
    )


@router.get("/staff", response_model=list[StaffOut])
def list_staff(db: DbSession, admin: AdminUser) -> list[StaffOut]:
    rows = db.execute(
        select(User).where(User.role == UserRole.ADMIN).order_by(User.created_at)
    ).scalars()
    return [StaffOut.model_validate(row) for row in rows]


@router.post("/staff", response_model=StaffPasswordOut, status_code=status.HTTP_201_CREATED)
def invite_staff(
    payload: StaffInviteIn, db: DbSession, settings: AppSettings, admin: AdminUser
) -> StaffPasswordOut:
    if UserRepository(db).get_by_email(payload.email) is not None:
        raise ConflictError("staff.email_taken", code="email_taken")
    user = User(
        email=payload.email.strip().lower(),
        display_name=payload.display_name.strip(),
        personal_phone_number=payload.phone,
        role=UserRole.ADMIN,
        staff_role=payload.staff_role,
    )
    db.add(user)
    db.flush()
    password = AuthService(db, settings).issue_password(user)
    db.refresh(user)
    return StaffPasswordOut(staff=StaffOut.model_validate(user), password=password)


@router.patch("/staff/{user_id}", response_model=StaffOut)
def update_staff(
    user_id: uuid.UUID, payload: StaffUpdateIn, db: DbSession, admin: AdminUser
) -> StaffOut:
    user = _load(db, user_id)
    if user.id == admin.id:
        raise ValidationError("staff.not_self", code="not_self")
    demoting = (
        payload.staff_role is not None and payload.staff_role is not StaffRole.MANAGER
    ) or payload.is_active is False
    if (
        demoting
        and user.staff_role is StaffRole.MANAGER
        and user.is_active
        and _active_managers(db) <= 1
    ):
        raise ValidationError("staff.last_manager", code="last_manager")
    if payload.staff_role is not None:
        user.staff_role = payload.staff_role
    if payload.is_active is not None and payload.is_active != user.is_active:
        user.is_active = payload.is_active
        # A disabled account's open sessions end now, not when they expire.
        user.token_version += 1
    db.commit()
    db.refresh(user)
    return StaffOut.model_validate(user)


@router.post("/staff/{user_id}/password", response_model=StaffPasswordOut)
def reissue_staff_password(
    user_id: uuid.UUID, db: DbSession, settings: AppSettings, admin: AdminUser
) -> StaffPasswordOut:
    user = _load(db, user_id)
    if user.id == admin.id:
        raise ValidationError("staff.not_self", code="not_self")
    password = AuthService(db, settings).issue_password(user)
    db.refresh(user)
    return StaffPasswordOut(staff=StaffOut.model_validate(user), password=password)
