"""Talent moderation workflow.

Deliberately a mirror of :mod:`app.services.moderation` rather than a shared
generic: the two write to different audit tables and will diverge (talent review
will want identity checks a shop listing does not), and the status machine is
short enough that duplicating it costs less than the indirection needed to share
it. The transition table below is the single source of truth for talent, exactly
as its business counterpart is for listings.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.core.i18n import LazyText
from app.models.enums import ModerationActionType
from app.models.talent import TalentModerationAction, TalentProfile
from app.models.user import User
from app.services.moderation import STATUS_LABEL_KEYS, TRANSITIONS

logger = logging.getLogger(__name__)

A = ModerationActionType


class TalentModerationService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _transition(
        self,
        profile: TalentProfile,
        action: ModerationActionType,
        *,
        actor: User,
        reason: str | None = None,
    ) -> TalentProfile:
        allowed_from, target = TRANSITIONS[action]
        if profile.status not in allowed_from:
            raise ConflictError(
                "moderation.invalid_transition",
                code="invalid_status_transition",
                details={"current_status": profile.status.value, "action": action.value},
                params={"status": LazyText(STATUS_LABEL_KEYS[profile.status])},
            )

        previous = profile.status
        now = datetime.now(UTC)
        profile.status = target

        if action is A.SUBMIT:
            profile.submitted_at = now
            # Clear the previous rejection so the owner's dashboard does not keep
            # showing a reason they have already addressed.
            profile.rejection_reason = None
        elif action is A.APPROVE:
            profile.approved_at = now
            profile.approved_by = actor.id
            profile.rejection_reason = None
        elif action is A.REJECT:
            profile.rejection_reason = reason
        elif action is A.REACTIVATE and profile.approved_at is None:
            profile.approved_at = now
            profile.approved_by = actor.id

        self._db.add(
            TalentModerationAction(
                profile_id=profile.id,
                admin_id=actor.id if actor.is_admin else None,
                actor_id=actor.id,
                action=action,
                from_status=previous,
                to_status=target,
                reason=reason,
            )
        )
        self._db.commit()

        logger.info(
            "Talent moderation transition",
            extra={
                "profile_id": str(profile.id),
                "action": action.value,
                "from_status": previous.value,
                "to_status": target.value,
                "actor_id": str(actor.id),
            },
        )
        return profile

    def submit_for_review(self, profile: TalentProfile, owner: User) -> TalentProfile:
        return self._transition(profile, A.SUBMIT, actor=owner)

    def approve(self, profile: TalentProfile, admin: User) -> TalentProfile:
        return self._transition(profile, A.APPROVE, actor=admin)

    def reject(self, profile: TalentProfile, admin: User, reason: str) -> TalentProfile:
        return self._transition(profile, A.REJECT, actor=admin, reason=reason)

    def suspend(
        self, profile: TalentProfile, admin: User, reason: str | None = None
    ) -> TalentProfile:
        return self._transition(profile, A.SUSPEND, actor=admin, reason=reason)

    def reactivate(self, profile: TalentProfile, admin: User) -> TalentProfile:
        return self._transition(profile, A.REACTIVATE, actor=admin)
