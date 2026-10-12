"""Someone offering to support the project: the partner form (round 3).

The owners asked for a card on the site -- in their words, someone who wants
to be a partner in supporting the people of the South -- leading to a short
form whose answers reach a page of the admin panel of their own.

Like a service request, it carries a stranger's name and phone number, so it
is read by administrators only: no public route reads it, and nothing about
it is published.
"""

from __future__ import annotations

import uuid

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, uuid_pk


class PartnerRequest(Base, TimestampMixin):
    __tablename__ = "partner_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    # What they do for a living, in their own words.
    occupation: Mapped[str] = mapped_column(String(160), nullable=False)
    residence: Mapped[str] = mapped_column(String(200), nullable=False)
    # What they would like to offer.
    offer: Mapped[str] = mapped_column(Text, nullable=False)
