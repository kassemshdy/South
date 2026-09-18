"""Testimonial lifecycle: submit, approve, hide, remove.

The state machine is small and the reasoning behind it is not, so it is
recorded here rather than inferred from the enum:

- **submit** is anonymous and rate limited. Nobody signs in, because
  requiring an account kills submissions from exactly the audience this
  project exists for, and verifying a phone number would imply an
  independence the feature does not have -- an owner can write and approve
  their own testimonial under any auth model, so verification buys the
  appearance of trust rather than trust itself. What keeps this honest is
  labelling it as owner-selected praise everywhere it is shown.
- **clear** and **reject** are the platform's, and come first. Submitted
  text is not shown to the owner until an administrator has looked at it:
  forwarding abuse to the person it was written about is precisely what a
  review gate is for, and "the owner can just hide it" means they read it.
- **approve** is the owner's, and is still the only route to a public
  payload. Both gates are load-bearing — the platform's answers for abuse,
  the owner's is what keeps this selected praise rather than a review
  system.
- **hide** takes one down again without deleting it, so the same text
  cannot quietly be resubmitted and re-approved, and an administrator can
  still see what was once published.
- **remove** is the administrator's, and is a real delete: the owner
  controls display, the platform keeps the last word on abuse.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import RateLimitedError
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.models.business import Business
from app.models.enums import TestimonialStatus
from app.models.testimonial import Testimonial
from app.repositories.testimonial import TestimonialRepository
from app.schemas.testimonial import TestimonialSubmitIn

# Only these ever reach a visitor. Named here so the public read has one
# definition rather than a status comparison repeated at each call site.
PUBLIC_STATUSES = (TestimonialStatus.APPROVED,)

# What the owner may see and act on: everything the platform has cleared.
# PENDING_REVIEW and REJECTED are deliberately absent — an owner is never
# shown text an administrator has not passed, which is the point of the gate.
OWNER_VISIBLE_STATUSES = (
    TestimonialStatus.PENDING_OWNER,
    TestimonialStatus.APPROVED,
    TestimonialStatus.HIDDEN,
)


class TestimonialService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._repo = TestimonialRepository(db)
        self._limiter = DatabaseRateLimiter(db)
        self._ip_rule = RateLimitRule(
            bucket="testimonial_submit_ip",
            limit=settings.testimonial_per_ip_limit,
            window_seconds=settings.testimonial_per_ip_window_seconds,
        )
        self._business_rule = RateLimitRule(
            bucket="testimonial_submit_business",
            limit=settings.testimonial_per_business_limit,
            window_seconds=settings.testimonial_per_business_window_seconds,
        )

    # --- Reading -----------------------------------------------------------

    def public_for(self, business: Business) -> list[Testimonial]:
        return self._repo.for_business(business.id, statuses=list(PUBLIC_STATUSES))

    def owner_for(self, business: Business) -> list[Testimonial]:
        """What the owner may act on -- platform-cleared states only."""
        return self._repo.for_business(
            business.id, statuses=list(OWNER_VISIBLE_STATUSES)
        )

    def all_for(self, business: Business) -> list[Testimonial]:
        """Every status, including the ones only an administrator sees."""
        return self._repo.for_business(business.id)

    # --- Writing -----------------------------------------------------------

    def submit(
        self,
        business: Business,
        payload: TestimonialSubmitIn,
        *,
        client_ip: str | None,
    ) -> Testimonial:
        """Record praise for review. Not shown to the owner, let alone a
        visitor, until an administrator has cleared it."""
        # Per-business first: it protects the person who would otherwise have
        # to read the flood, and it holds even when the sender rotates address.
        business_status = self._limiter.hit(self._business_rule, str(business.id))
        if not business_status.allowed:
            raise RateLimitedError(
                business_status.retry_after_seconds, "testimonial.rate_limited"
            )
        if client_ip:
            ip_status = self._limiter.hit(self._ip_rule, client_ip)
            if not ip_status.allowed:
                raise RateLimitedError(
                    ip_status.retry_after_seconds, "testimonial.rate_limited"
                )

        testimonial = Testimonial(
            business_id=business.id,
            author_name=payload.author_name.strip(),
            body=payload.body.strip(),
            status=TestimonialStatus.PENDING_REVIEW,
        )
        self._repo.add(testimonial)
        self._db.commit()
        return testimonial

    def clear(self, testimonial: Testimonial) -> Testimonial:
        """Platform gate passed: hand it to the owner to decide on."""
        testimonial.status = TestimonialStatus.PENDING_OWNER
        self._db.commit()
        return testimonial

    def reject(self, testimonial: Testimonial) -> Testimonial:
        """Refused by the platform. Never reaches the owner or the page."""
        testimonial.status = TestimonialStatus.REJECTED
        self._db.commit()
        return testimonial

    def approve(self, testimonial: Testimonial) -> Testimonial:
        testimonial.status = TestimonialStatus.APPROVED
        testimonial.approved_at = datetime.now(UTC)
        self._db.commit()
        return testimonial

    def hide(self, testimonial: Testimonial) -> Testimonial:
        testimonial.status = TestimonialStatus.HIDDEN
        self._db.commit()
        return testimonial

    def remove(self, testimonial: Testimonial) -> None:
        self._repo.delete(testimonial)
        self._db.commit()
