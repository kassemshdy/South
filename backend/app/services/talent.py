"""Talent profile lifecycle: create, update, and keep the search haystack in sync."""

from __future__ import annotations

import logging
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.core.arabic import build_search_text
from app.core.candidate_text import contains_contact_details, is_person_name
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.i18n import LazyJoin
from app.core.urls import normalize_social_url, normalize_url, youtube_video_id
from app.core.work_videos import parse_work_video
from app.models.enums import BusinessStatus, TalentKind, ViewSubject, WorkMode
from app.models.talent import (
    TalentCourse,
    TalentEducation,
    TalentExperience,
    TalentFaq,
    TalentLanguage,
    TalentProfile,
    TalentServiceOffer,
    TalentSocialLink,
    TalentVideo,
    TalentWorkArea,
    TalentWorkTypeRow,
)
from app.models.user import User
from app.repositories.talent import TalentRepository, TalentSkillRepository
from app.repositories.taxonomy import LocationRepository
from app.schemas.business import SocialLinkIn
from app.schemas.talent import (
    TalentCreateIn,
    TalentEducationIn,
    TalentExperienceIn,
    TalentLanguageIn,
    TalentUpdateIn,
)
from app.services.analytics import ViewCounterService
from app.services.slug import unique_slug
from app.services.verification import has_identity_document

logger = logging.getLogger(__name__)

# Fields a person must supply before their profile can be reviewed. Kept here
# rather than in the schema because they are required *at submission*, not at
# save: the editor deliberately allows saving an incomplete draft.
SUBMISSION_REQUIREMENTS: tuple[tuple[str, str], ...] = (
    ("display_name", "talent.field.display_name"),
    ("bio", "talent.field.bio"),
    ("skill_id", "talent.field.skill"),
    ("location_id", "talent.field.location"),
)


class TalentService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = TalentRepository(db)
        self._skills = TalentSkillRepository(db)
        self._locations = LocationRepository(db)
        # Photos of offers an update removed; the route deletes the files,
        # as it holds the storage backend.
        self.removed_image_keys: list[str] = []

    # --- Creation and updates ---------------------------------------------

    def create(self, owner: User, payload: TalentCreateIn) -> TalentProfile:
        # One profile per account. Checked here rather than relying on the
        # unique index so the caller gets a translated 409 instead of an
        # IntegrityError surfacing as a 500.
        if self._repo.get_for_owner(owner.id) is not None:
            raise ConflictError("talent.already_exists", code="talent_profile_exists")

        self._validate_taxonomy(payload.skill_id, payload.location_id)
        kind = payload.kind or TalentKind.SERVICE
        self._check_candidate_text(kind, payload.display_name, payload.bio)

        profile = TalentProfile(
            owner_id=owner.id,
            display_name=payload.display_name,
            kind=payload.kind or TalentKind.SERVICE,
            slug=unique_slug(
                payload.display_name, self._repo.slug_exists, fallback_prefix="talent"
            ),
            bio=payload.bio,
            years_experience=payload.years_experience,
            skill_id=payload.skill_id,
            custom_skill_text=payload.custom_skill_text,
            skill_specialty=payload.skill_specialty,
            preferred_contact=payload.preferred_contact,
            location_id=payload.location_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            phone=payload.phone,
            whatsapp=payload.whatsapp,
            phone_public=payload.phone_public is not False,
            email=payload.email,
            website=normalize_url(payload.website) if payload.website else None,
            youtube_video_id=(
                youtube_video_id(payload.video_url) if payload.video_url else None
            ),
            status=BusinessStatus.DRAFT,
            highest_degree=payload.highest_degree,
            specialization=payload.specialization,
            university=payload.university,
            education_years=payload.education_years,
            graduation_date=payload.graduation_date,
            study_focus=payload.study_focus,
            experience=payload.experience,
            professional_training=payload.professional_training,
            skills_text=payload.skills_text,
            services_offered=payload.services_offered,
            hobbies=payload.hobbies,
            employment_type=payload.employment_type,
            remote_capable=_remote_capable(payload.work_mode, payload.remote_capable),
            work_mode=payload.work_mode,
            desired_title=payload.desired_title,
            education_level=payload.education_level,
            team_message=payload.team_message,
        )
        for flag in ("availability", "photo_hidden", "cv_public"):
            value = getattr(payload, flag)
            if value is not None:
                setattr(profile, flag, value)
        if payload.languages is not None:
            self._apply_languages(profile, payload.languages)
        self._apply_candidate_lists(profile, payload.model_dump(exclude_unset=True), payload)
        if payload.social_links:
            self._apply_social_links(profile, payload.social_links)
        # Add (and flush) before deriving the haystack: on a transient object
        # not yet attached to the session, relationship access (profile.skill,
        # profile.location) silently returns None regardless of the FK columns
        # above, which would index every new profile with a blank skill and
        # location.
        self._repo.add(profile)
        profile.search_text = self._build_search_text(profile)

        self._db.commit()
        logger.info(
            "Talent profile created",
            extra={"profile_id": str(profile.id), "owner_id": str(owner.id)},
        )
        return self._reload(profile.id)

    def update(self, profile: TalentProfile, payload: TalentUpdateIn) -> TalentProfile:
        data = payload.model_dump(exclude_unset=True)

        if "skill_id" in data or "location_id" in data:
            self._validate_taxonomy(
                data.get("skill_id", profile.skill_id),
                data.get("location_id", profile.location_id),
            )

        if "website" in data:
            data["website"] = normalize_url(data["website"]) if data["website"] else None
        # The request carries a link and the column holds an id, so this key
        # is replaced rather than passed through to setattr.
        if "video_url" in data:
            raw_video = data.pop("video_url")
            data["youtube_video_id"] = youtube_video_id(raw_video) if raw_video else None

        # A relationship, not a column: model_dump turned it into a list of
        # dicts, which setattr would happily assign and then fail on flush.
        languages = data.pop("languages", None)
        social_links = data.pop("social_links", None)
        lists = {
            key: data.pop(key)
            for key in (
                "work_types",
                "work_area_ids",
                "experiences",
                "service_offers",
                "faqs",
                "work_videos",
                "education",
                "courses",
            )
            if key in data
        }
        # Not nullable: an explicit null means "no change".
        for flag in ("availability", "photo_hidden", "cv_public"):
            if flag in data and data[flag] is None:
                data.pop(flag)

        self._check_candidate_text(
            data.get("kind") or profile.kind,
            data.get("display_name"),
            data.get("bio"),
        )

        if "work_mode" in data:
            data["remote_capable"] = _remote_capable(
                data["work_mode"], data.get("remote_capable", profile.remote_capable)
            )

        for field, value in data.items():
            setattr(profile, field, value)

        if languages is not None:
            self._apply_languages(profile, payload.languages or [])
        if social_links is not None:
            self._apply_social_links(profile, payload.social_links or [])
        self._apply_candidate_lists(profile, lists, payload)

        # The slug is part of the public URL; renaming must not break links that
        # are already shared, so it is only derived once at creation.
        profile.search_text = self._build_search_text(profile)

        self._db.commit()
        logger.info("Talent profile updated", extra={"profile_id": str(profile.id)})
        return self._reload(profile.id)

    def delete(self, profile: TalentProfile) -> None:
        # Images cascade at the database level; storage objects are cleaned up
        # by the caller, which holds the storage backend.
        profile_id = profile.id
        # View counters do not cascade -- see ViewSubject for why there is no
        # foreign key to hang ON DELETE off.
        ViewCounterService(self._db).forget(ViewSubject.TALENT, profile_id)
        self._repo.delete(profile)
        self._db.commit()
        logger.info("Talent profile deleted", extra={"profile_id": str(profile_id)})

    # --- Submission readiness ---------------------------------------------

    def missing_requirements(self, profile: TalentProfile) -> list[str]:
        """Translation keys for the fields still needed before review.

        Keys rather than text: the caller renders them in the reader's locale.
        """
        missing = [
            key
            for field, key in SUBMISSION_REQUIREMENTS
            if not getattr(profile, field, None)
        ]
        # Checked against None rather than for truth: 0 is an answer -- someone
        # just starting out -- and the owners made the question compulsory.
        # A job application only; optional for a service (12 Nov 2026).
        if profile.kind == TalentKind.JOB_SEEKER and profile.years_experience is None:
            missing.append("talent.field.years_experience")
        # The owners made a pin compulsory for every seller; the town is
        # enough. Checked against None: 0.0 is a coordinate.
        if profile.latitude is None or profile.longitude is None:
            missing.append("talent.field.map_pin")
        if not profile.photo_url:
            missing.append("talent.field.photo")
        # No cover is asked for any more: the owners dropped the wide cover
        # (10 Nov 2026), so the photo is the one picture review needs.
        if not (profile.phone or profile.whatsapp):
            missing.append("talent.field.contact")
        # The owner's ID, as for a shop (the owners' decision, 9 Nov 2026).
        if not has_identity_document(self._db, profile.owner_id):
            missing.append("talent.field.identity")
        # The owners made it compulsory for a service; a job application is
        # not asked.
        if profile.kind == TalentKind.SERVICE and profile.work_mode is None:
            missing.append("talent.field.work_mode")
        if (
            profile.skill is not None
            and profile.skill.slug == "other"
            and not (profile.custom_skill_text or "").strip()
        ):
            missing.append("talent.field.custom_skill")
        return missing

    def assert_ready_for_review(self, profile: TalentProfile) -> None:
        missing = self.missing_requirements(profile)
        if missing:
            raise ValidationError(
                "talent.incomplete",
                code="incomplete_talent_profile",
                details={"missing": missing},
                params={"missing": LazyJoin(tuple(missing))},
            )

    # --- internals ---------------------------------------------------------

    @staticmethod
    def _check_candidate_text(
        kind: TalentKind, display_name: str | None, bio: str | None
    ) -> None:
        """A job seeker's name is a person's name, and their bio carries no
        contact details (see app.core.candidate_text). Checked only on what
        is being saved, so an older profile can still be edited elsewhere."""
        if kind is not TalentKind.JOB_SEEKER:
            return
        if display_name is not None and not is_person_name(display_name):
            raise ValidationError("talent.name_not_person", code="name_not_person")
        if contains_contact_details(bio):
            raise ValidationError("talent.bio_has_contact", code="bio_has_contact")

    def _apply_candidate_lists(
        self,
        profile: TalentProfile,
        data: dict[str, object],
        payload: TalentCreateIn | TalentUpdateIn,
    ) -> None:
        """Replace each list the request carried, as languages are."""
        if "work_types" in data:
            profile.work_types.clear()
            for work_type in dict.fromkeys(payload.work_types or []):
                profile.work_types.append(TalentWorkTypeRow(work_type=work_type))
        if "work_area_ids" in data:
            ids = list(dict.fromkeys(payload.work_area_ids or []))
            for location_id in ids:
                if self._locations.get(location_id) is None:
                    raise ValidationError("talent.unknown_location", code="unknown_location")
            profile.work_areas.clear()
            for location_id in ids:
                profile.work_areas.append(TalentWorkArea(location_id=location_id))
        if "experiences" in data:
            self._apply_experiences(profile, payload.experiences or [])
            # Counted from the entries unless the person gave a number.
            if payload.years_experience is None and profile.experiences:
                profile.years_experience = _years_from(payload.experiences or [])
        if "service_offers" in data:
            # Matched by id rather than replaced, so an offer's photo
            # survives an edit of the profile (12 Nov 2026). An offer left
            # out is removed, and its photo with it.
            existing = {offer.id: offer for offer in profile.service_offers}
            kept: list[TalentServiceOffer] = []
            for index, offer in enumerate(payload.service_offers or []):
                saved = existing.pop(offer.id, None) if offer.id is not None else None
                if saved is None:
                    saved = TalentServiceOffer()
                saved.title = offer.title
                saved.description = offer.description
                saved.price_from = offer.price_from
                saved.price_to = offer.price_to
                saved.currency = offer.currency
                saved.price_unit = offer.price_unit
                saved.sort_order = index
                kept.append(saved)
            self.removed_image_keys.extend(
                offer.image_storage_key
                for offer in existing.values()
                if offer.image_storage_key
            )
            profile.service_offers[:] = kept
        if "work_videos" in data:
            # Every link checked before any is kept: one bad link refuses
            # the save rather than dropping silently.
            videos = [
                parse_work_video(raw) for raw in payload.work_videos or [] if raw.strip()
            ]
            profile.work_videos.clear()
            for index, video in enumerate(videos):
                profile.work_videos.append(
                    TalentVideo(platform=video.platform, key=video.key, sort_order=index)
                )
        if "faqs" in data:
            profile.faqs.clear()
            for index, faq in enumerate(payload.faqs or []):
                profile.faqs.append(
                    TalentFaq(question=faq.question, answer=faq.answer, sort_order=index)
                )
        if "education" in data:
            profile.education.clear()
            for index, row in enumerate(payload.education or []):
                profile.education.append(_education_row(row, index))
        if "courses" in data:
            profile.courses.clear()
            for index, course in enumerate(payload.courses or []):
                profile.courses.append(
                    TalentCourse(
                        name=course.name, issuer=course.issuer, year=course.year, sort_order=index
                    )
                )

    @staticmethod
    def _apply_experiences(profile: TalentProfile, entries: list[TalentExperienceIn]) -> None:
        profile.experiences.clear()
        for index, entry in enumerate(entries):
            profile.experiences.append(
                TalentExperience(
                    title=entry.title,
                    employer=entry.employer,
                    town=entry.town,
                    start_date=entry.start_date,
                    end_date=None if entry.is_current else entry.end_date,
                    is_current=entry.is_current,
                    description=entry.description,
                    sort_order=index,
                )
            )

    def _reload(self, profile_id: uuid.UUID) -> TalentProfile:
        profile = self._repo.get_with_relations(profile_id)
        if profile is None:  # pragma: no cover - only on concurrent deletion
            raise NotFoundError("talent.not_found")
        return profile

    def _validate_taxonomy(
        self, skill_id: uuid.UUID | None, location_id: uuid.UUID | None
    ) -> None:
        if skill_id is not None and self._skills.get(skill_id) is None:
            raise ValidationError("talent.unknown_skill", code="unknown_skill")
        if location_id is not None and self._locations.get(location_id) is None:
            raise ValidationError("talent.unknown_location", code="unknown_location")

    def _apply_languages(
        self, profile: TalentProfile, languages: list[TalentLanguageIn]
    ) -> None:
        """Replace the whole set rather than diffing it.

        The editor submits the list it wants to end up with, and these rows
        carry nothing worth preserving across an edit (no id the client
        knows, no created_at anyone reads), so a wholesale replace is both
        simpler and impossible to leave half-applied.
        """
        profile.languages.clear()
        for index, language in enumerate(languages):
            profile.languages.append(
                TalentLanguage(
                    name=language.name,
                    proficiency=language.proficiency,
                    sort_order=index,
                )
            )

    def _apply_social_links(self, profile: TalentProfile, links: list[SocialLinkIn]) -> None:
        """Replace the whole set, one link per platform, empty ones dropped.

        The same rules as a shop's links: a platform named twice is refused
        rather than one of the two silently kept, and each URL goes through
        the same normaliser, so a bare handle becomes a full link.
        """
        seen: set[str] = set()
        normalized: list[TalentSocialLink] = []
        for link in links:
            if not link.url or not link.url.strip():
                continue
            if link.platform.value in seen:
                raise ConflictError(
                    "business.duplicate_social_platform",
                    code="duplicate_social_platform",
                )
            seen.add(link.platform.value)
            normalized.append(
                TalentSocialLink(
                    platform=link.platform,
                    url=normalize_social_url(link.platform, link.url),
                )
            )
        profile.social_links.clear()
        self._db.flush()
        profile.social_links.extend(normalized)

    def _build_search_text(self, profile: TalentProfile) -> str:
        if profile.skill is None:
            skill = ""
        elif profile.skill.slug == "other" and profile.custom_skill_text:
            # Otherwise every "Other" profile would index the same literal skill
            # name and none of them would be findable by what they actually do.
            skill = profile.custom_skill_text
        else:
            skill = profile.skill.name_ar
        location = profile.location.name_ar if profile.location else ""
        # The identity fields are deliberately absent: search is a public
        # endpoint, so indexing a legal name or a civil-registration place
        # would let anyone find a profile by data the profile never shows.
        return build_search_text(
            profile.display_name,
            profile.bio,
            skill,
            # Indexed beside the taxonomy skill rather than instead of it.
            # Someone looking for a teacher of one particular subject is
            # searching the specialty; without this, only the broad skill
            # name would match, hiding exactly the profiles this field
            # exists to describe.
            profile.skill_specialty,
            # The job a candidate is asking for is what an employer types.
            profile.desired_title,
            location,
            profile.skills_text,
            profile.services_offered,
        )


def _education_row(row: TalentEducationIn, index: int) -> TalentEducation:
    return TalentEducation(
        degree=row.degree,
        field=row.field,
        institution=row.institution,
        graduation_year=row.graduation_year,
        sort_order=index,
    )


def _years_from(entries: list[TalentExperienceIn]) -> int:
    """Whole years covered by the entries, overlaps counted once."""
    today = date.today()
    spans = sorted(
        (entry.start_date, today if entry.is_current else (entry.end_date or entry.start_date))
        for entry in entries
        if entry.start_date is not None
    )
    total = 0
    current_start: date | None = None
    current_end: date | None = None
    for start, end in spans:
        end = max(start, end)
        if current_end is None or start > current_end:
            if current_start is not None and current_end is not None:
                total += (current_end - current_start).days
            current_start, current_end = start, end
        else:
            current_end = max(current_end, end)
    if current_start is not None and current_end is not None:
        total += (current_end - current_start).days
    return min(70, total // 365)


def _remote_capable(work_mode: WorkMode | None, fallback: bool) -> bool:
    """The old flag, kept in step with the answer that replaced it."""
    if work_mode is None:
        return fallback
    return work_mode in (WorkMode.REMOTE, WorkMode.BOTH)
