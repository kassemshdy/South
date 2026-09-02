"""Moderation workflow.

The status machine is written out explicitly rather than scattered across
endpoints: one table below defines every legal transition, and every transition
writes an audit row. Adding moderation of *edits* to an approved listing later
means adding transitions here, not rewriting the API.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.models.business import Business, ModerationAction
from app.models.enums import BusinessStatus, ModerationActionType
from app.models.user import User

logger = logging.getLogger(__name__)

S = BusinessStatus
A = ModerationActionType

# action -> (allowed source statuses, resulting status)
TRANSITIONS: dict[ModerationActionType, tuple[frozenset[BusinessStatus], BusinessStatus]] = {
    A.SUBMIT: (frozenset({S.DRAFT, S.REJECTED}), S.PENDING_REVIEW),
    A.APPROVE: (frozenset({S.PENDING_REVIEW}), S.APPROVED),
    A.REJECT: (frozenset({S.PENDING_REVIEW}), S.REJECTED),
    A.SUSPEND: (frozenset({S.APPROVED}), S.SUSPENDED),
    A.REACTIVATE: (frozenset({S.SUSPENDED}), S.APPROVED),
}

STATUS_LABELS_AR: dict[BusinessStatus, str] = {
    S.DRAFT: "مسودة",
    S.PENDING_REVIEW: "قيد المراجعة",
    S.APPROVED: "مقبول",
    S.REJECTED: "يحتاج إلى تعديل",
    S.SUSPENDED: "موقوف",
}


class ModerationService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _transition(
        self,
        business: Business,
        action: ModerationActionType,
        *,
        actor: User,
        reason: str | None = None,
    ) -> Business:
        allowed_from, target = TRANSITIONS[action]
        if business.status not in allowed_from:
            raise ConflictError(
                f"لا يمكن تنفيذ هذا الإجراء والنشاط في حالة «{STATUS_LABELS_AR[business.status]}».",
                code="invalid_status_transition",
                details={"current_status": business.status.value, "action": action.value},
            )

        previous = business.status
        now = datetime.now(UTC)
        business.status = target

        if action is A.SUBMIT:
            business.submitted_at = now
            # Clear the previous rejection so the owner's dashboard does not keep
            # showing a reason they have already addressed.
            business.rejection_reason = None
        elif action is A.APPROVE:
            business.approved_at = now
            business.approved_by = actor.id
            business.rejection_reason = None
        elif action is A.REJECT:
            business.rejection_reason = reason
        elif action is A.REACTIVATE and business.approved_at is None:
            business.approved_at = now
            business.approved_by = actor.id

        self._db.add(
            ModerationAction(
                business_id=business.id,
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
            "Business moderation transition",
            extra={
                "business_id": str(business.id),
                "action": action.value,
                "from_status": previous.value,
                "to_status": target.value,
                "actor_id": str(actor.id),
            },
        )
        return business

    def submit_for_review(self, business: Business, owner: User) -> Business:
        return self._transition(business, A.SUBMIT, actor=owner)

    def approve(self, business: Business, admin: User) -> Business:
        return self._transition(business, A.APPROVE, actor=admin)

    def reject(self, business: Business, admin: User, reason: str) -> Business:
        return self._transition(business, A.REJECT, actor=admin, reason=reason)

    def suspend(self, business: Business, admin: User, reason: str | None = None) -> Business:
        return self._transition(business, A.SUSPEND, actor=admin, reason=reason)

    def reactivate(self, business: Business, admin: User) -> Business:
        return self._transition(business, A.REACTIVATE, actor=admin)
