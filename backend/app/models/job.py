"""Job openings the platform posts, and the applications people send to them.

The owners' request (29 Oct 2026, the job openings ticket): an administrator adds
each opening by hand -- for an employer in the South, or the platform's own --
and a visitor applies with their name, email, phone and CV. Unlike a
job seeker's profile (``/jobs``), an opening is written by staff, has a draft
and published switch, and may close on a deadline.

An employer may also offer a job on a public form (the same ticket's
description): it arrives as a **draft** opening carrying who sent it --
their name, phone and ID scan -- which no public schema carries, and an
administrator checks it before publishing.

An application is a stranger's contact details and CV, so like a workshop
sign-up it is read by staff only, and the CV by reviewers and the manager
(``RESTRICTED_READS``). The CV sits in a private storage folder the media
mount refuses (``app.services.job_applications.STORAGE_FOLDERS``).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, pg_enum, uuid_pk
from app.models.enums import JobType, WorkMode

if TYPE_CHECKING:
    from app.models.taxonomy import Location


class JobOpening(Base, TimestampMixin):
    __tablename__ = "job_openings"
    __table_args__ = (Index("ix_job_openings_published", "is_published", "created_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    employer_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    job_type: Mapped[JobType] = mapped_column(
        pg_enum(JobType, "job_type"), nullable=False, default=JobType.FULL_TIME
    )
    #: Free text ("$600 a month", "by agreement"), so nothing is invented.
    salary: Mapped[str | None] = mapped_column(String(120), nullable=True)
    #: Last day applications are taken; none means open until unpublished.
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    #: Where the work is, in the employer's words, and how it is done.
    work_place: Mapped[str | None] = mapped_column(String(200), nullable=True)
    work_mode: Mapped[WorkMode | None] = mapped_column(
        pg_enum(WorkMode, "work_mode"), nullable=True
    )

    # Set only when an employer offered the job on the public form. Staff
    # read them; no public schema carries any of them.
    submitter_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    submitter_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    id_document_storage_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    id_document_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    #: A thumbnail chosen by staff, shown on the list and the page.
    cover_url: Mapped[str | None] = mapped_column(String, nullable=True)
    cover_storage_key: Mapped[str | None] = mapped_column(String, nullable=True)

    location: Mapped[Location | None] = relationship(lazy="joined")
    applications: Mapped[list[JobApplication]] = relationship(
        back_populates="job", cascade="all, delete-orphan", passive_deletes=True
    )


class JobApplication(Base, TimestampMixin):
    __tablename__ = "job_applications"

    id: Mapped[uuid.UUID] = uuid_pk()
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_openings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    #: The CV. Named ``storage_key`` so the Telegram archive attaches it like
    #: every other private document (only with TELEGRAM_SEND_FILES on).
    storage_key: Mapped[str] = mapped_column(String(300), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    job: Mapped[JobOpening] = relationship(back_populates="applications")
