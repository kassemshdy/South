from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.i18n import translate
from app.models.enums import BusinessStatus, ModerationActionType, UserRole
from app.schemas.business import OwnerBusinessOut
from app.schemas.common import ORMModel
from app.schemas.talent import OwnerTalentOut


class ModerationActionOut(ORMModel):
    id: uuid.UUID
    action: ModerationActionType
    from_status: BusinessStatus | None = None
    to_status: BusinessStatus
    reason: str | None = None
    created_at: datetime


class RejectIn(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)

    @field_validator("reason")
    @classmethod
    def _strip(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 5:
            raise ValueError(translate("moderation.reject_reason_required"))
        return cleaned


class SuspendIn(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class AdminUserOut(ORMModel):
    id: uuid.UUID
    phone_number: str | None
    personal_phone_number: str | None
    email: str | None
    display_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    business_count: int = 0


class AdminBusinessOut(OwnerBusinessOut):
    """Full review payload, including the owner's contact details."""

    owner_phone: str | None = None
    owner_personal_phone: str | None = None
    owner_has_verification_document: bool = False
    owner_display_name: str | None = None
    owner_id: uuid.UUID
    moderation_actions: list[ModerationActionOut] = Field(default_factory=list)


class AdminTalentOut(OwnerTalentOut):
    """Full review payload, including the account's contact details."""

    owner_phone: str | None = None
    owner_personal_phone: str | None = None
    owner_has_verification_document: bool = False
    owner_display_name: str | None = None
    owner_id: uuid.UUID
    moderation_actions: list[ModerationActionOut] = Field(default_factory=list)


class AdminUserDetailOut(AdminUserOut):
    """The account list's row, plus everything it owns — every business (in
    any status, not just APPROVED) and its talent profile if it has one — so
    an administrator can go from a user straight to reviewing what they've
    listed, website link included, without hunting through /admin/businesses
    by owner phone number."""

    businesses: list[AdminBusinessOut] = Field(default_factory=list)
    talent_profile: AdminTalentOut | None = None
