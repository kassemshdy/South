"""An employer's contact form on a candidate's page, and the admin's log of them.

The candidate directory ticket (the owners', 31 Oct 2026) replaces the
service request form on a job seeker's page with "have a job for this
candidate?". It differs from a service request in who reads it:

- **Logged for the team, not the candidate's dashboard.** The ticket asks for
  every request in an admin list with a status, so the platform can count
  placements, and for the request to reach the candidate on WhatsApp. There
  is no WhatsApp gateway, so a person relays it: the admin list carries the
  candidate's number and the Telegram archive posts each new request.
- **Anonymous and rate limited**, for the reasons recorded on
  :mod:`app.services.service_request`, with the same limits.
- **Job seekers only.** A service profile keeps its own request form.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings
from app.core.errors import NotFoundError, RateLimitedError
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.models.enums import EmployerRequestStatus, TalentKind
from app.models.talent import EmployerRequest, TalentProfile
from app.schemas.talent import EmployerRequestIn


class EmployerRequestService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._limiter = DatabaseRateLimiter(db)
        self._ip_rule = RateLimitRule(
            bucket="employer_request_ip",
            limit=settings.service_request_per_ip_limit,
            window_seconds=settings.service_request_per_ip_window_seconds,
        )
        self._profile_rule = RateLimitRule(
            bucket="employer_request_profile",
            limit=settings.service_request_per_profile_limit,
            window_seconds=settings.service_request_per_profile_window_seconds,
        )

    def place(
        self, profile: TalentProfile, payload: EmployerRequestIn, *, client_ip: str | None
    ) -> EmployerRequest:
        if profile.kind is not TalentKind.JOB_SEEKER:
            raise NotFoundError("talent.not_public")
        for rule, key in ((self._profile_rule, str(profile.id)), (self._ip_rule, client_ip)):
            if not key:
                continue
            status = self._limiter.hit(rule, key)
            if not status.allowed:
                raise RateLimitedError(
                    status.retry_after_seconds, "employer_request.rate_limited"
                )
        request = EmployerRequest(
            profile_id=profile.id,
            employer_name=payload.employer_name,
            phone=payload.phone,
            company=payload.company,
            job_title=payload.job_title,
            message=(payload.message or "").strip() or None,
            status=EmployerRequestStatus.NEW,
        )
        self._db.add(request)
        self._db.commit()
        return request

    def list_all(self, status: EmployerRequestStatus | None = None) -> list[EmployerRequest]:
        stmt = (
            select(EmployerRequest)
            .options(joinedload(EmployerRequest.profile))
            .order_by(EmployerRequest.created_at.desc())
            .limit(500)
        )
        if status is not None:
            stmt = stmt.where(EmployerRequest.status == status)
        return list(self._db.execute(stmt).scalars().all())

    def set_status(
        self, request_id: uuid.UUID, status: EmployerRequestStatus
    ) -> EmployerRequest:
        request = self._db.get(EmployerRequest, request_id)
        if request is None:
            raise NotFoundError("employer_request.not_found")
        request.status = status
        self._db.commit()
        return request
