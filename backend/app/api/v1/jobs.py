"""Job openings: read by anyone, written by administrators.

The owners' request (29 Oct 2026, the job openings ticket). An opening is
published by hand like a workshop and stays listed until it is unpublished.

Since the jobs redesign (31 Oct 2026) nobody applies through the site: an
opening carries a number to contact by WhatsApp or a call, and a status --
open, filled, no longer available -- that is separate from publishing. A
closed opening keeps its page, so a shared link still opens and says so; an
open one whose deadline has passed reads as no longer available. Presses of
the two buttons are counted per day, with nothing about who pressed.

Applications sent before the redesign stay in the database for staff, and
are deleted with their opening; nothing writes new ones.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, Path, Response, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.captcha import verify_captcha
from app.core.dependencies import AdminUser, AppSettings, ClientIp, Crawler, DbSession
from app.core.downloads import content_disposition
from app.core.errors import ConflictError, NotFoundError, RateLimitedError
from app.core.i18n import translate
from app.core.phone import normalize_phone
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.core.uploads import read_at_most
from app.models.enums import ImageKind, JobContactChannel, JobStatus
from app.models.job import JobApplication, JobContactClickDaily, JobOpening
from app.models.site_setting import SiteSetting
from app.models.taxonomy import Location
from app.schemas.common import MessageResponse
from app.schemas.job import (
    AdminJobOpeningOut,
    JobApplicationOut,
    JobContactClickIn,
    JobContactDayOut,
    JobContactStatsOut,
    JobOfferIn,
    JobOpeningIn,
    JobOpeningOut,
    JobOpeningUpdateIn,
)
from app.services.images import ImageService
from app.services.job_applications import EMPLOYER_ID_FOLDER, JobCvService
from app.services.slug import slugify_name, unique_slug
from app.storage.factory import get_storage

public_router = APIRouter(tags=["jobs"])
admin_router = APIRouter(prefix="/admin/job-openings", tags=["admin-jobs"])

MAX_LISTED = 60


def _today() -> date:
    return datetime.now(UTC).date()


def _published(db: DbSession) -> Select[tuple[JobOpening]]:
    """What a visitor may read: every published opening, closed ones included."""
    return select(JobOpening).where(JobOpening.is_published.is_(True))


def effective_status(job: JobOpening) -> JobStatus:
    """The status a visitor sees: an open opening past its deadline has closed."""
    if job.status is JobStatus.ACTIVE and job.deadline is not None and job.deadline < _today():
        return JobStatus.UNAVAILABLE
    return job.status


def _status_changed_at(job: JobOpening) -> datetime | None:
    if job.status is JobStatus.ACTIVE and effective_status(job) is JobStatus.UNAVAILABLE:
        assert job.deadline is not None
        # It closed the day after its deadline.
        return datetime(job.deadline.year, job.deadline.month, job.deadline.day, tzinfo=UTC)
    return job.status_changed_at


def _site_whatsapp(db: DbSession) -> str | None:
    row = db.get(SiteSetting, "contact_whatsapp")
    if row is None or not row.value:
        return None
    try:
        return normalize_phone(row.value)
    except Exception:
        return row.value


def _public_out(db: DbSession, job: JobOpening, fallback: str | None = None) -> JobOpeningOut:
    return JobOpeningOut.model_validate(job).model_copy(
        update={
            "status": effective_status(job),
            "status_changed_at": _status_changed_at(job),
            "contact_phone": job.contact_phone or fallback or _site_whatsapp(db),
        }
    )


def open_slugs(db: DbSession) -> list[tuple[str, datetime]]:
    """(slug, updated_at) of every published opening, for the sitemap."""
    public = _published(db).subquery()
    rows = db.execute(select(public.c.slug, public.c.updated_at)).all()
    return [(row[0], row[1]) for row in rows]


def _slug_exists(db: DbSession, slug: str, exclude_id: uuid.UUID | None = None) -> bool:
    stmt = select(JobOpening.id).where(JobOpening.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(JobOpening.id != exclude_id)
    return db.execute(stmt.limit(1)).scalar_one_or_none() is not None


def _limit(db: DbSession, settings: AppSettings, client_ip: str | None, bucket: str) -> None:
    """The partner form's limits: per address, and for the whole site per day."""
    limiter = DatabaseRateLimiter(db)
    if client_ip:
        per_ip = limiter.hit(
            RateLimitRule(
                bucket=f"{bucket}_ip",
                limit=settings.partner_per_ip_limit,
                window_seconds=settings.partner_per_ip_window_seconds,
            ),
            client_ip,
        )
        if not per_ip.allowed:
            raise RateLimitedError(per_ip.retry_after_seconds, "job.rate_limited")
    overall = limiter.hit(
        RateLimitRule(
            bucket=f"{bucket}_global",
            limit=settings.partner_per_day_limit,
            window_seconds=86400,
        ),
        "all",
    )
    if not overall.allowed:
        raise RateLimitedError(overall.retry_after_seconds, "job.rate_limited")


# --- Public ----------------------------------------------------------------


@public_router.get("/job-openings", response_model=list[JobOpeningOut])
def list_job_openings(db: DbSession) -> list[JobOpeningOut]:
    """Open openings first, the newest first; then closed ones, the latest closed first."""
    stmt = _published(db).order_by(JobOpening.created_at.desc()).limit(MAX_LISTED)
    fallback = _site_whatsapp(db)
    jobs = [_public_out(db, job, fallback) for job in db.execute(stmt).unique().scalars()]
    open_ = [job for job in jobs if job.status is JobStatus.ACTIVE]
    closed = sorted(
        (job for job in jobs if job.status is not JobStatus.ACTIVE),
        key=lambda job: job.status_changed_at or job.created_at,
        reverse=True,
    )
    return open_ + closed


def _published_or_404(db: DbSession, slug: str) -> JobOpening:
    job = db.execute(_published(db).where(JobOpening.slug == slug)).unique().scalar_one_or_none()
    if job is None:
        raise NotFoundError("job.not_found")
    return job


@public_router.get("/job-openings/{slug}", response_model=JobOpeningOut)
def get_job_opening(slug: Annotated[str, Path(max_length=180)], db: DbSession) -> JobOpeningOut:
    """A published opening, open or closed: a shared link keeps working."""
    return _public_out(db, _published_or_404(db, slug))


@public_router.post(
    "/job-openings/{slug}/contact-click", status_code=204, response_class=Response
)
def count_job_contact_click(
    slug: Annotated[str, Path(max_length=180)],
    payload: JobContactClickIn,
    db: DbSession,
    crawler: Crawler,
) -> Response:
    """Count a press of an open opening's WhatsApp or call button.

    Stores an integer per opening, channel and day, and nothing about the
    caller. A closed opening shows no buttons, so it counts nothing.
    """
    job = _published_or_404(db, slug)
    if crawler or effective_status(job) is not JobStatus.ACTIVE:
        return Response(status_code=204)
    stmt = (
        insert(JobContactClickDaily)
        .values(id=uuid.uuid4(), job_id=job.id, channel=payload.channel, day=_today(), clicks=1)
        .on_conflict_do_update(
            constraint="uq_job_contact_click_daily",
            set_={"clicks": JobContactClickDaily.clicks + 1},
        )
    )
    db.execute(stmt)
    db.commit()
    return Response(status_code=204)


@public_router.post(
    "/job-openings/offer",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def offer_a_job(
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
    submitter_name: Annotated[str, Form()],
    phone_number: Annotated[str, Form()],
    employer_name: Annotated[str, Form()],
    work_place: Annotated[str, Form()],
    work_mode: Annotated[str, Form()],
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    id_document: Annotated[UploadFile, File(description="The employer's ID: PDF, JPEG or PNG")],
    captcha_token: Annotated[str | None, Form()] = None,
) -> MessageResponse:
    """An employer offers a job for a southerner (the owners' ticket).

    It becomes a **draft** opening: nothing is published until an
    administrator has read it. Who sent it -- name, phone, ID scan -- is kept
    on the row for staff and never reaches a public payload.
    """
    try:
        payload = JobOfferIn(
            submitter_name=submitter_name,
            phone_number=phone_number,
            employer_name=employer_name,
            work_place=work_place,
            work_mode=work_mode,  # type: ignore[arg-type]
            title=title,
            description=description,
            captcha_token=captcha_token,
        )
    except PydanticValidationError as exc:
        raise RequestValidationError(
            [{**error, "loc": ("body", *error["loc"])} for error in exc.errors()]
        ) from exc

    _limit(db, settings, client_ip, "job_offer")
    verify_captcha(payload.captcha_token, settings, client_ip=client_ip)

    files = JobCvService(get_storage(), settings)
    data = read_at_most(id_document.file, settings.max_verification_doc_bytes)
    content_type = files.validate(data)
    job = JobOpening(
        slug=unique_slug(payload.title, lambda s: _slug_exists(db, s), fallback_prefix="job"),
        title=payload.title,
        description=payload.description,
        employer_name=payload.employer_name,
        work_place=payload.work_place,
        work_mode=payload.work_mode,
        submitter_name=payload.submitter_name,
        submitter_phone=payload.phone_number,
        is_published=False,
    )
    db.add(job)
    db.flush()
    key = files.store(
        job_id=job.id, data=data, content_type=content_type, folder=EMPLOYER_ID_FOLDER
    )
    job.id_document_storage_key = key
    job.id_document_content_type = content_type
    try:
        db.commit()
    except Exception:
        files.delete(key)
        raise
    return MessageResponse(message=translate("job.offer_received"))


# --- Administrators --------------------------------------------------------


def _get_or_404(db: DbSession, job_id: uuid.UUID) -> JobOpening:
    job = db.get(JobOpening, job_id)
    if job is None:
        raise NotFoundError("job.not_found")
    return job


def _check_location(db: DbSession, location_id: uuid.UUID | None) -> None:
    if location_id is not None and db.get(Location, location_id) is None:
        raise NotFoundError("taxonomy.location.not_found")


def _admin_out(db: DbSession, job: JobOpening, fallback: str | None = None) -> AdminJobOpeningOut:
    clicks = db.execute(
        select(func.coalesce(func.sum(JobContactClickDaily.clicks), 0)).where(
            JobContactClickDaily.job_id == job.id
        )
    ).scalar_one()
    public = _public_out(db, job, fallback)
    return AdminJobOpeningOut.model_validate(job).model_copy(
        update={
            **public.model_dump(include={"status", "status_changed_at", "contact_phone"}),
            "saved_status": job.status,
            "own_contact_phone": job.contact_phone,
            "contact_clicks": int(clicks),
            "has_id_document": job.id_document_storage_key is not None,
            "application_count": int(
                db.execute(
                    select(func.count()).where(JobApplication.job_id == job.id)
                ).scalar_one()
            ),
        }
    )


@admin_router.get("", response_model=list[AdminJobOpeningOut])
def admin_list_job_openings(db: DbSession, admin: AdminUser) -> list[AdminJobOpeningOut]:
    """Every opening, drafts and closed ones included, the newest first."""
    jobs = db.execute(select(JobOpening).order_by(JobOpening.created_at.desc())).unique()
    fallback = _site_whatsapp(db)
    return [_admin_out(db, job, fallback) for job in jobs.scalars()]


@admin_router.post("", response_model=AdminJobOpeningOut, status_code=status.HTTP_201_CREATED)
def create_job_opening(
    payload: JobOpeningIn, db: DbSession, admin: AdminUser
) -> AdminJobOpeningOut:
    slug = (
        slugify_name(payload.slug, fallback_prefix="job")
        if payload.slug
        else unique_slug(payload.title, lambda s: _slug_exists(db, s), fallback_prefix="job")
    )
    if _slug_exists(db, slug):
        raise ConflictError("job.duplicate_slug", code="duplicate_slug")
    _check_location(db, payload.location_id)
    job = JobOpening(slug=slug, **payload.model_dump(exclude={"slug"}))
    job.status_changed_at = datetime.now(UTC)
    db.add(job)
    db.commit()
    db.refresh(job)
    return _admin_out(db, job)


@admin_router.put("/{job_id}", response_model=AdminJobOpeningOut)
def update_job_opening(
    job_id: uuid.UUID, payload: JobOpeningUpdateIn, db: DbSession, admin: AdminUser
) -> AdminJobOpeningOut:
    job = _get_or_404(db, job_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("slug"):
        slug = slugify_name(data["slug"], fallback_prefix="job")
        if _slug_exists(db, slug, exclude_id=job_id):
            raise ConflictError("job.duplicate_slug", code="duplicate_slug")
        data["slug"] = slug
    _check_location(db, data.get("location_id"))
    if "status" in data and data["status"] is None:
        del data["status"]
    if "whatsapp_enabled" in data and data["whatsapp_enabled"] is None:
        del data["whatsapp_enabled"]
    if "status" in data and data["status"] is not job.status:
        job.status_changed_at = datetime.now(UTC)
    for field, value in data.items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return _admin_out(db, job)


@admin_router.post("/{job_id}/publish", response_model=AdminJobOpeningOut)
def publish_job_opening(job_id: uuid.UUID, db: DbSession, admin: AdminUser) -> AdminJobOpeningOut:
    job = _get_or_404(db, job_id)
    job.is_published = True
    db.commit()
    return _admin_out(db, job)


@admin_router.post("/{job_id}/unpublish", response_model=AdminJobOpeningOut)
def unpublish_job_opening(
    job_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> AdminJobOpeningOut:
    job = _get_or_404(db, job_id)
    job.is_published = False
    db.commit()
    return _admin_out(db, job)


@admin_router.delete("/{job_id}", response_model=MessageResponse)
def delete_job_opening(
    job_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> MessageResponse:
    """The opening, every application to it, and every CV they carried."""
    job = _get_or_404(db, job_id)
    keys = [application.storage_key for application in job.applications]
    if job.id_document_storage_key:
        keys.append(job.id_document_storage_key)
    cover_key = job.cover_storage_key
    db.delete(job)
    db.commit()
    cvs = JobCvService(get_storage(), settings)
    for key in keys:
        cvs.delete(key)
    ImageService(get_storage(), settings).delete(cover_key)
    return MessageResponse(message=translate("job.deleted"))


@admin_router.post("/{job_id}/image", response_model=AdminJobOpeningOut)
def upload_job_opening_cover(
    job_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="Thumbnail image")],
) -> AdminJobOpeningOut:
    """Set or replace the opening's thumbnail; the old file is removed."""
    job = _get_or_404(db, job_id)
    service = ImageService(get_storage(), settings)
    service.delete(job.cover_storage_key)
    stored = service.process_and_store(
        data=read_at_most(file.file, settings.max_upload_bytes),
        content_type=file.content_type,
        owner_id=job.id,
        kind=ImageKind.COVER,
        prefix="jobs",
    )
    job.cover_url, job.cover_storage_key = stored.url, stored.key
    db.commit()
    return _admin_out(db, job)


@admin_router.delete("/{job_id}/image", response_model=AdminJobOpeningOut)
def delete_job_opening_cover(
    job_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> AdminJobOpeningOut:
    job = _get_or_404(db, job_id)
    ImageService(get_storage(), settings).delete(job.cover_storage_key)
    job.cover_url, job.cover_storage_key = None, None
    db.commit()
    return _admin_out(db, job)


@admin_router.get("/{job_id}/applications", response_model=list[JobApplicationOut])
def list_job_applications(
    job_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> list[JobApplicationOut]:
    """Applications sent through the old form, the latest first. Read-only:
    applying moved to WhatsApp and calls, and these stay readable rather
    than lost (the owners' decision, 3 Nov 2026)."""
    _get_or_404(db, job_id)
    rows = db.execute(
        select(JobApplication)
        .where(JobApplication.job_id == job_id)
        .order_by(JobApplication.created_at.desc())
    ).scalars()
    return [JobApplicationOut.model_validate(row) for row in rows]


@admin_router.get("/{job_id}/applications/{application_id}/cv")
def download_job_application_cv(
    job_id: uuid.UUID,
    application_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
) -> Response:
    application = db.get(JobApplication, application_id)
    if application is None or application.job_id != job_id:
        raise NotFoundError("job.application_not_found")
    data = JobCvService(get_storage(), settings).read(application.storage_key)
    return Response(
        content=data,
        media_type=application.content_type,
        headers={
            "Content-Disposition": content_disposition(
                application.original_filename or f"cv-{application.id}"
            ),
            "Cache-Control": "no-store",
        },
    )


@admin_router.get("/{job_id}/id-document")
def download_job_offer_id_document(
    job_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> Response:
    """The ID scan an employer sent with the job they offered."""
    job = _get_or_404(db, job_id)
    if not job.id_document_storage_key:
        raise NotFoundError("job.id_document_not_found")
    data = JobCvService(get_storage(), settings).read(job.id_document_storage_key)
    return Response(
        content=data,
        media_type=job.id_document_content_type or "application/octet-stream",
        headers={
            "Content-Disposition": content_disposition(f"id-{job.slug}"),
            "Cache-Control": "no-store",
        },
    )


@admin_router.get("/{job_id}/contact-clicks", response_model=JobContactStatsOut)
def job_contact_clicks(job_id: uuid.UUID, db: DbSession, admin: AdminUser) -> JobContactStatsOut:
    """Presses of the opening's WhatsApp and call buttons, per day."""
    _get_or_404(db, job_id)
    rows = db.execute(
        select(JobContactClickDaily.day, JobContactClickDaily.channel, JobContactClickDaily.clicks)
        .where(JobContactClickDaily.job_id == job_id)
        .order_by(JobContactClickDaily.day.desc())
    ).all()
    days: dict[date, JobContactDayOut] = {}
    totals = {JobContactChannel.WHATSAPP: 0, JobContactChannel.CALL: 0}
    for day, channel, clicks in rows:
        entry = days.setdefault(day, JobContactDayOut(day=day))
        if channel is JobContactChannel.WHATSAPP:
            entry.whatsapp += clicks
        else:
            entry.call += clicks
        totals[channel] += clicks
    return JobContactStatsOut(
        whatsapp=totals[JobContactChannel.WHATSAPP],
        call=totals[JobContactChannel.CALL],
        days=list(days.values()),
    )
