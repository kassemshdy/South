"""A visitor asking the team for a service, without choosing a provider.

The owners' services redesign (3 Nov 2026): "request a service". Where a request on
a profile goes to that provider only (``service_request.py``), this one is
addressed to the team, who find someone suitable and pass it on -- so here
an administrator read is the point rather than a leak. The skill and the
town are optional hints for that search.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.talent import TalentSkill
    from app.models.taxonomy import Location


class OpenServiceRequest(Base, TimestampMixin):
    __tablename__ = "open_service_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    customer_name: Mapped[str] = mapped_column(String(80), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("talent_skills.id", ondelete="SET NULL"), nullable=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    # Set when a member of staff has dealt with it: it moves to the archive
    # rather than being deleted, as partner requests do.
    solved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    skill: Mapped[TalentSkill | None] = relationship()
    location: Mapped[Location | None] = relationship()
