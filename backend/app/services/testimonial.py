"""Testimonial lifecycle: submit, approve, reject, remove.

The state machine is small and the reasoning behind it is not, so it is
recorded here rather than inferred from the enum:

- **submit** is anonymous and rate limited, on a business or a service
  profile. Nobody signs in, because requiring an account kills submissions
  from exactly the audience this project exists for.
- **approve** and **reject** are the administrator's, and approve is the
  only route to a public payload. Nothing is published before a person has
  read it, because open praise in a small region carries real social risk.
  The listing's owner used to approve as well; the owners removed that step
  (round 3), so the owner reads what is published and decides nothing.
- **remove** is the administrator's too, and is a real delete.

Every published rating counts toward the listing's stars -- see
``_refresh_rating``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import RateLimitedError
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.models.business import Business
from app.models.enums import TestimonialStatus
from app.models.talent import TalentProfile
from app.models.testimonial import Testimonial
from app.repositories.testimonial import TestimonialRepository
from app.schemas.testimonial import TestimonialSubmitIn

# Only these ever reach a visitor -- or the listing's owner, who reads the
# page as a visitor would. Named here so the reads have one definition rather
# than a status comparison repeated at each call site.
PUBLIC_STATUSES = (TestimonialStatus.APPROVED,)

Subject = Business | TalentProfile


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

    def public_for(self, subject: Subject) -> list[Testimonial]:
        return self._repo.for_subject(subject, statuses=list(PUBLIC_STATUSES))

    def all_for(self, subject: Subject) -> list[Testimonial]:
        """Every status, including the ones only an administrator sees."""
        return self._repo.for_subject(subject)

    # --- Writing -----------------------------------------------------------

    def submit(
        self,
        subject: Subject,
        payload: TestimonialSubmitIn,
        *,
        client_ip: str | None,
    ) -> Testimonial:
        """Record praise for review. Not shown to anyone but an administrator
        until one has approved it."""
        # Per-listing first: it protects the person who would otherwise have
        # to read the flood, and it holds even when the sender rotates address.
        # The bucket is keyed by id, and a business and a profile never share
        # one, so the existing bucket name serves both.
        subject_status = self._limiter.hit(self._business_rule, str(subject.id))
        if not subject_status.allowed:
            raise RateLimitedError(
                subject_status.retry_after_seconds, "testimonial.rate_limited"
            )
        if client_ip:
            ip_status = self._limiter.hit(self._ip_rule, client_ip)
            if not ip_status.allowed:
                raise RateLimitedError(
                    ip_status.retry_after_seconds, "testimonial.rate_limited"
                )

        testimonial = Testimonial(
            author_name=payload.author_name.strip(),
            body=payload.body.strip(),
            rating=payload.rating,
            status=TestimonialStatus.PENDING_REVIEW,
        )
        if isinstance(subject, Business):
            testimonial.business_id = subject.id
        else:
            testimonial.talent_profile_id = subject.id
        self._repo.add(testimonial)
        self._db.commit()
        return testimonial

    def approve(self, testimonial: Testimonial) -> Testimonial:
        """Publish it. The only route by which a testimonial becomes visible."""
        testimonial.status = TestimonialStatus.APPROVED
        testimonial.approved_at = datetime.now(UTC)
        self._refresh_rating(testimonial)
        self._db.commit()
        return testimonial

    def reject(self, testimonial: Testimonial) -> Testimonial:
        """Refused. Never reaches the page; taken down if it was on it."""
        testimonial.status = TestimonialStatus.REJECTED
        self._refresh_rating(testimonial)
        self._db.commit()
        return testimonial

    def remove(self, testimonial: Testimonial) -> None:
        self._repo.delete(testimonial)
        self._refresh_rating(testimonial)
        self._db.commit()

    def _refresh_rating(self, testimonial: Testimonial) -> None:
        """Recount the stars a visitor can see on this listing.

        Every published rating counts -- the owners' decision -- and only
        published ones, so the average is exactly the average of what the
        page shows and a visitor can check it.
        """
        self._db.flush()
        subject: Subject | None
        if testimonial.business_id is not None:
            column = Testimonial.business_id
            subject_id: uuid.UUID = testimonial.business_id
            subject = self._db.get(Business, subject_id)
        elif testimonial.talent_profile_id is not None:
            column = Testimonial.talent_profile_id
            subject_id = testimonial.talent_profile_id
            subject = self._db.get(TalentProfile, subject_id)
        else:
            return
        if subject is None:
            return
        average, count = self._db.execute(
            select(func.avg(Testimonial.rating), func.count(Testimonial.rating)).where(
                column == subject_id,
                Testimonial.status == TestimonialStatus.APPROVED,
                Testimonial.rating.is_not(None),
            )
        ).one()
        subject.rating_count = int(count)
        subject.rating_average = round(float(average), 2) if count else None
