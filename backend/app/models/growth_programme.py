"""The growth programme (the owners' decision, 18 Nov 2026).

Staff pick about fifty serious, responsive shops and take each one through
the same steps -- contact and review of its social accounts, AI-made
content, a full listing, a Shopify store, then ad credit -- to make them
Janoubona's success stories. One row per shop in the programme: where it
is, a note, and a snapshot of its numbers on the day it joined, so the
admin page can show "before" beside "now".

Staff-only: no public route reads it, and no owner sees it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.user import User

#: The steps, in order. Stored as text so a step can be added without a
#: migration; the API refuses anything else.
GROWTH_STAGES = ("CONTACTED", "CONTENT", "LISTING", "SHOPIFY", "ADS")


class GrowthEnrollment(Base, TimestampMixin):
    __tablename__ = "growth_enrollments"

    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    stage: Mapped[str] = mapped_column(String(20), nullable=False, default="CONTACTED")
    stage_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    enrolled_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Its numbers on the day it joined: followers then, and views and
    # contact-button presses over the 30 days before.
    baseline_instagram: Mapped[int | None] = mapped_column(Integer, nullable=True)
    baseline_facebook: Mapped[int | None] = mapped_column(Integer, nullable=True)
    baseline_views_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    baseline_clicks_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    business: Mapped[Business] = relationship()
    enrolled_by: Mapped[User | None] = relationship()
