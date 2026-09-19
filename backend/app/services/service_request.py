"""Asking a talent profile for a piece of work, and its owner working through it.

The same decisions as :mod:`app.services.order`, for the same reasons, and
they are restated here rather than cross-referenced because someone changing
one should have to decide about the other:

- **Anonymous, rate limited.** A junk request costs the person one message
  and a row to mark handled. Against that, a sign-in would sit between a
  real customer and the single action the feature exists to produce.
- **No notification.** There is no email infrastructure here and Twilio costs
  per message, so nothing pings the provider in this slice and no string
  claims otherwise. The request is in their dashboard and the requester still
  gets the WhatsApp handoff.
- **No administrator view.** A request carries a third party's name and
  phone. Moderation needs neither.

The one difference from an order is what is being asked for. An order names
catalogue items, each checked against the listing in the path, so most of
that service is validation. A talent profile has no catalogue: the
description *is* the request, and the only thing to establish is that the
profile is one a visitor may see at all.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import RateLimitedError
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.models.enums import OrderStatus
from app.models.service_request import ServiceRequest
from app.models.talent import TalentProfile
from app.repositories.service_request import ServiceRequestRepository
from app.schemas.service_request import ServiceRequestCreateIn


class ServiceRequestService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._repo = ServiceRequestRepository(db)
        self._limiter = DatabaseRateLimiter(db)
        self._ip_rule = RateLimitRule(
            bucket="service_request_ip",
            limit=settings.service_request_per_ip_limit,
            window_seconds=settings.service_request_per_ip_window_seconds,
        )
        self._profile_rule = RateLimitRule(
            bucket="service_request_profile",
            limit=settings.service_request_per_profile_limit,
            window_seconds=settings.service_request_per_profile_window_seconds,
        )

    def for_profile(self, profile: TalentProfile) -> list[ServiceRequest]:
        return self._repo.for_profile(profile.id)

    def place(
        self,
        profile: TalentProfile,
        payload: ServiceRequestCreateIn,
        *,
        client_ip: str | None,
    ) -> ServiceRequest:
        # Per-profile first: it protects the person who would otherwise have
        # to wade through the flood, and it holds when the sender rotates
        # address.
        profile_status = self._limiter.hit(self._profile_rule, str(profile.id))
        if not profile_status.allowed:
            raise RateLimitedError(
                profile_status.retry_after_seconds, "service_request.rate_limited"
            )
        if client_ip:
            ip_status = self._limiter.hit(self._ip_rule, client_ip)
            if not ip_status.allowed:
                raise RateLimitedError(
                    ip_status.retry_after_seconds, "service_request.rate_limited"
                )

        request = ServiceRequest(
            profile_id=profile.id,
            customer_name=payload.customer_name.strip(),
            customer_phone=payload.customer_phone,
            details=payload.details,
            status=OrderStatus.NEW,
        )
        self._repo.add(request)
        self._db.commit()
        return request

    def set_status(self, request: ServiceRequest, status: OrderStatus) -> ServiceRequest:
        request.status = status
        self._db.commit()
        return request
