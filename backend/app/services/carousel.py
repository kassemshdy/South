"""The announcements carousel: one ordered list of slides for two pages.

The owners' ticket (31 Oct 2026): the same carousel at the top of
/activities and on the home page, in an order an administrator sets on one
screen, with slides that are an activity's photograph or a custom image of
their own (a partner banner, a campaign).

- **Adding is automatic.** An activity gets a slide, first in line, the
  first time it has a photograph and is kept; the administrator can take it
  out again, and it stays out until somebody puts it back.
- **Removing never touches the activity.** It stays on the activities list.
- **Archived and finished activities leave on their own**: archiving
  deletes the slide, and with ``carousel_autoremove_expired`` on (the
  default) a finished activity is simply not shown.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import NotFoundError, ValidationError
from app.models.activity import Activity, CarouselSlide
from app.models.site_setting import SiteSetting

AUTOREMOVE_KEY = "carousel_autoremove_expired"


def has_ended(activity: Activity, now: datetime | None = None) -> bool:
    """Finished: its end has passed, or its start when it gives no end."""
    end = activity.ends_at or activity.starts_at
    return end is not None and end < (now or datetime.now(UTC))


class CarouselService:
    def __init__(self, db: Session) -> None:
        self._db = db

    # --- settings ----------------------------------------------------------

    def autoremove_expired(self) -> bool:
        row = self._db.get(SiteSetting, AUTOREMOVE_KEY)
        return row is None or row.value != "false"

    def set_autoremove_expired(self, value: bool) -> None:
        row = self._db.get(SiteSetting, AUTOREMOVE_KEY)
        text = "true" if value else "false"
        if row is None:
            self._db.add(SiteSetting(key=AUTOREMOVE_KEY, value=text))
        else:
            row.value = text
        self._db.commit()

    # --- reading -----------------------------------------------------------

    def all(self) -> list[CarouselSlide]:
        stmt = (
            select(CarouselSlide)
            .options(joinedload(CarouselSlide.activity))
            .order_by(CarouselSlide.position.asc(), CarouselSlide.created_at.desc())
        )
        return list(self._db.execute(stmt).scalars().all())

    def visible(self) -> list[CarouselSlide]:
        """What a visitor sees: custom slides with an image, and activities
        that are public (kept, with a photograph) and, with auto-removal on,
        not finished."""
        autoremove = self.autoremove_expired()
        now = datetime.now(UTC)
        shown: list[CarouselSlide] = []
        for slide in self.all():
            activity = slide.activity
            if activity is None:
                if slide.activity_id is None and slide.image_url:
                    shown.append(slide)
                continue
            if activity.is_archived or not activity.image_url:
                continue
            if autoremove and has_ended(activity, now):
                continue
            shown.append(slide)
        return shown

    def slide_for(self, activity_id: uuid.UUID) -> CarouselSlide | None:
        return self._db.execute(
            select(CarouselSlide).where(CarouselSlide.activity_id == activity_id)
        ).scalar_one_or_none()

    # --- writing -----------------------------------------------------------

    def _first_position(self) -> int:
        lowest = self._db.execute(select(func.min(CarouselSlide.position))).scalar_one_or_none()
        return (lowest if lowest is not None else 1) - 1

    def add_activity(self, activity: Activity, *, commit: bool = True) -> CarouselSlide:
        """Put an activity first in the carousel; a no-op when it is there."""
        if not activity.image_url:
            raise ValidationError("carousel.needs_image", code="carousel_needs_image")
        existing = self.slide_for(activity.id)
        if existing is not None:
            return existing
        slide = CarouselSlide(activity_id=activity.id, position=self._first_position())
        self._db.add(slide)
        if commit:
            self._db.commit()
        return slide

    def remove_activity(self, activity: Activity, *, commit: bool = True) -> None:
        slide = self.slide_for(activity.id)
        if slide is not None:
            self._db.delete(slide)
            if commit:
                self._db.commit()

    def add_custom(
        self,
        *,
        image_url: str,
        image_storage_key: str,
        title: str | None,
        link_url: str | None,
    ) -> CarouselSlide:
        slide = CarouselSlide(
            position=self._first_position(),
            image_url=image_url,
            image_storage_key=image_storage_key,
            title=title,
            link_url=link_url,
        )
        self._db.add(slide)
        self._db.commit()
        return slide

    def get(self, slide_id: uuid.UUID) -> CarouselSlide:
        slide = self._db.get(CarouselSlide, slide_id)
        if slide is None:
            raise NotFoundError("carousel.not_found")
        return slide

    def reorder(self, slide_ids: list[uuid.UUID]) -> None:
        """The slides in this order; any slide not named keeps its place
        after them."""
        slides = {slide.id: slide for slide in self.all()}
        if any(slide_id not in slides for slide_id in slide_ids):
            raise NotFoundError("carousel.not_found")
        ordered = list(dict.fromkeys(slide_ids)) + [
            slide_id for slide_id in slides if slide_id not in slide_ids
        ]
        for position, slide_id in enumerate(ordered):
            slides[slide_id].position = position
        self._db.commit()

    def delete(self, slide: CarouselSlide) -> str | None:
        """Remove a slide; returns the custom image's storage key to delete."""
        key = slide.image_storage_key if slide.activity_id is None else None
        self._db.delete(slide)
        self._db.commit()
        return key
