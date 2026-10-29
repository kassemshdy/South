"""Job openings: read and applied to by anyone, written by administrators.

The owners' request (29 Oct 2026, the job openings ticket). An opening is
published by hand like a workshop and stays listed until it is unpublished
or its deadline passes. Applying is the workshop sign-up's shape -- anonymous,
behind a per-address and a site-wide limit and the captcha when one is
configured -- plus a CV, which is checked before anything is stored and kept
in a folder the media mount refuses. Applications are read by staff; the CV
itself by reviewers and the manager (``RESTRICTED_READS``).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, Path, Response, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import Select, func, or_, select

from app.core.captcha import verify_captcha
from app.core.dependencies import AdminUser, AppSettings, ClientIp, DbSession
from app.core.downloads import content_disposition
from app.core.errors import ConflictError, NotFoundError, RateLimitedError
from app.core.i18n import translate
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.core.uploads import read_at_most
from app.models.job import JobApplication, JobOpening
from app.models.taxonomy import Location
from app.schemas.common import MessageResponse
from app.schemas.job import (
    AdminJobOpeningOut,
    JobApplicationIn,
    JobApplicationOut,
    JobOpeningIn,
    JobOpeningOut,
    JobOpeningUpdateIn,
)
from app.services.job_applications import JobCvService
from app.services.slug import slugify_name, unique_slug
from app.storage.factory import get_storage

public_router = APIRouter(tags=["jobs"])
admin_router = APIRouter(prefix="/admin/job-openings", tags=["admin-jobs"])

MAX_LISTED = 60


def _today() -> date:
    return datetime.now(UTC).date()


def _open(db: DbSession) -> Select[tuple[JobOpening]]:
    """Published, and not past its deadline: what a visitor may read and apply to."""
    return select(JobOpening).where(
        JobOpening.is_published.is_(True),
        or_(JobOpening.deadline.is_(None), JobOpening.deadline >= _today()),
    )


def open_slugs(db: DbSession) -> list[tuple[str, datetime]]:
    """(slug, updated_at) of every open opening, for the sitemap."""
    public = _open(db).subquery()
    rows = db.execute(select(public.c.slug, public.c.updated_at)).all()
    return [(row[0], row[1]) for row in rows]


def _slug_exists(db: DbSession, slug: str, exclude_id: uuid.UUID | None = None) -> bool:
    stmt = select(JobOpening.id).where(JobOpening.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(JobOpening.id != exclude_id)
    return db.execute(stmt.limit(1)).scalar_one_or_none() is not None


# --- Public ----------------------------------------------------------------


@public_router.get("/job-openings", response_model=list[JobOpeningOut])
def list_job_openings(db: DbSession) -> list[JobOpeningOut]:
    """Open job openings, the newest first."""
    stmt = _open(db).order_by(JobOpening.created_at.desc()).limit(MAX_LISTED)
    return [JobOpeningOut.model_validate(job) for job in db.execute(stmt).unique().scalars()]


@public_router.get("/job-openings/{slug}", response_model=JobOpeningOut)
def get_job_opening(slug: Annotated[str, Path(max_length=180)], db: DbSession) -> JobOpeningOut:
    job = db.execute(_open(db).where(JobOpening.slug == slug)).unique().scalar_one_or_none()
    if job is None:
        raise NotFoundError("job.not_found")
    return JobOpeningOut.model_validate(job)


@public_router.post(
    "/job-openings/{slug}/apply",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_to_job(
    slug: Annotated[str, Path(max_length=180)],
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
    full_name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    phone_number: Annotated[str, Form()],
    cv: Annotated[UploadFile, File(description="The applicant's CV: PDF, JPEG or PNG")],
    captcha_token: Annotated[str | None, Form()] = None,
) -> MessageResponse:
    try:
        payload = JobApplicationIn(
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            captcha_token=captcha_token,
        )
    except PydanticValidationError as exc:
        raise RequestValidationError(
            [{**error, "loc": ("body", *error["loc"])} for error in exc.errors()]
        ) from exc

    job = db.execute(_open(db).where(JobOpening.slug == slug)).unique().scalar_one_or_none()
    if job is None:
        raise NotFoundError("job.not_found")

    limiter = DatabaseRateLimiter(db)
    if client_ip:
        per_ip = limiter.hit(
            RateLimitRule(
                bucket="job_apply_ip",
                limit=settings.partner_per_ip_limit,
                window_seconds=settings.partner_per_ip_window_seconds,
            ),
            client_ip,
        )
        if not per_ip.allowed:
            raise RateLimitedError(per_ip.retry_after_seconds, "job.rate_limited")
    overall = limiter.hit(
        RateLimitRule(
            bucket="job_apply_global",
            limit=settings.partner_per_day_limit,
            window_seconds=86400,
        ),
        "all",
    )
    if not overall.allowed:
        raise RateLimitedError(overall.retry_after_seconds, "job.rate_limited")
    verify_captcha(payload.captcha_token, settings, client_ip=client_ip)

    # Read bounded, then refused before any row exists if it is not a document.
    cvs = JobCvService(get_storage(), settings)
    data = read_at_most(cv.file, settings.max_verification_doc_bytes)
    content_type = cvs.validate(data)
    key = cvs.store(job_id=job.id, data=data, content_type=content_type)
    try:
        db.add(
            JobApplication(
                job_id=job.id,
                full_name=payload.full_name,
                email=str(payload.email),
                phone_number=payload.phone_number,
                storage_key=key,
                content_type=content_type,
                original_filename=cv.filename[:255] if cv.filename else None,
                size_bytes=len(data),
            )
        )
        db.commit()
    except Exception:
        cvs.delete(key)
        raise
    return MessageResponse(message=translate("job.applied"))


# --- Administrators --------------------------------------------------------


def _get_or_404(db: DbSession, job_id: uuid.UUID) -> JobOpening:
    job = db.get(JobOpening, job_id)
    if job is None:
        raise NotFoundError("job.not_found")
    return job


def _check_location(db: DbSession, location_id: uuid.UUID | None) -> None:
    if location_id is not None and db.get(Location, location_id) is None:
        raise NotFoundError("taxonomy.location.not_found")


def _admin_out(db: DbSession, job: JobOpening) -> AdminJobOpeningOut:
    count = db.execute(
        select(func.count()).select_from(JobApplication).where(JobApplication.job_id == job.id)
    ).scalar_one()
    return AdminJobOpeningOut.model_validate(job).model_copy(
        update={"application_count": int(count)}
    )


@admin_router.get("", response_model=list[AdminJobOpeningOut])
def admin_list_job_openings(db: DbSession, admin: AdminUser) -> list[AdminJobOpeningOut]:
    """Every opening, drafts and closed ones included, the newest first."""
    jobs = db.execute(select(JobOpening).order_by(JobOpening.created_at.desc())).unique()
    return [_admin_out(db, job) for job in jobs.scalars()]


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
    db.delete(job)
    db.commit()
    cvs = JobCvService(get_storage(), settings)
    for key in keys:
        cvs.delete(key)
    return MessageResponse(message=translate("job.deleted"))


@admin_router.get("/{job_id}/applications", response_model=list[JobApplicationOut])
def list_job_applications(
    job_id: uuid.UUID, db: DbSession, admin: AdminUser
) -> list[JobApplicationOut]:
    """Who applied, the earliest first."""
    _get_or_404(db, job_id)
    rows = db.execute(
        select(JobApplication)
        .where(JobApplication.job_id == job_id)
        .order_by(JobApplication.created_at.asc())
    ).scalars()
    return [JobApplicationOut.model_validate(row) for row in rows]


def _application_or_404(
    db: DbSession, job_id: uuid.UUID, application_id: uuid.UUID
) -> JobApplication:
    application = db.get(JobApplication, application_id)
    if application is None or application.job_id != job_id:
        raise NotFoundError("job.application_not_found")
    return application


@admin_router.get("/{job_id}/applications/{application_id}/cv")
def download_job_application_cv(
    job_id: uuid.UUID,
    application_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
) -> Response:
    application = _application_or_404(db, job_id, application_id)
    data = JobCvService(get_storage(), settings).read(application.storage_key)
    filename = application.original_filename or f"cv-{application.id}"
    return Response(
        content=data,
        media_type=application.content_type,
        headers={
            "Content-Disposition": content_disposition(filename),
            "Cache-Control": "no-store",
        },
    )


@admin_router.delete("/{job_id}/applications/{application_id}", response_model=MessageResponse)
def delete_job_application(
    job_id: uuid.UUID,
    application_id: uuid.UUID,
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
) -> MessageResponse:
    """An application and its CV, gone for good (an applicant may ask)."""
    application = _application_or_404(db, job_id, application_id)
    key = application.storage_key
    db.delete(application)
    db.commit()
    JobCvService(get_storage(), settings).delete(key)
    return MessageResponse(message=translate("job.application_deleted"))
