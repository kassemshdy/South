"""Talent profile lifecycle: create, update, and keep the search haystack in sync."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.arabic import build_search_text
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.i18n import LazyJoin
from app.core.urls import normalize_url
from app.models.enums import BusinessStatus
from app.models.talent import TalentLanguage, TalentProfile
from app.models.user import User
from app.repositories.talent import TalentRepository, TalentSkillRepository
from app.repositories.taxonomy import LocationRepository
from app.schemas.talent import TalentCreateIn, TalentLanguageIn, TalentUpdateIn
from app.services.slug import unique_slug

logger = logging.getLogger(__name__)

# Fields a person must supply before their profile can be reviewed. Kept here
# rather than in the schema because they are required *at submission*, not at
# save: the editor deliberately allows saving an incomplete draft.
SUBMISSION_REQUIREMENTS: tuple[tuple[str, str], ...] = (
    ("display_name", "talent.field.display_name"),
    ("headline", "talent.field.headline"),
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

    # --- Creation and updates ---------------------------------------------

    def create(self, owner: User, payload: TalentCreateIn) -> TalentProfile:
        # One profile per account. Checked here rather than relying on the
        # unique index so the caller gets a translated 409 instead of an
        # IntegrityError surfacing as a 500.
        if self._repo.get_for_owner(owner.id) is not None:
            raise ConflictError("talent.already_exists", code="talent_profile_exists")

        self._validate_taxonomy(payload.skill_id, payload.location_id)

        profile = TalentProfile(
            owner_id=owner.id,
            display_name=payload.display_name,
            slug=unique_slug(
                payload.display_name, self._repo.slug_exists, fallback_prefix="talent"
            ),
            headline=payload.headline,
            bio=payload.bio,
            years_experience=payload.years_experience,
            skill_id=payload.skill_id,
            custom_skill_text=payload.custom_skill_text,
            location_id=payload.location_id,
            phone=payload.phone,
            whatsapp=payload.whatsapp,
            email=payload.email,
            website=normalize_url(payload.website) if payload.website else None,
            status=BusinessStatus.DRAFT,
            highest_degree=payload.highest_degree,
            specialization=payload.specialization,
            university=payload.university,
            experience=payload.experience,
            skills_text=payload.skills_text,
            services_offered=payload.services_offered,
        )
        if payload.languages is not None:
            self._apply_languages(profile, payload.languages)
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

        # A relationship, not a column: model_dump turned it into a list of
        # dicts, which setattr would happily assign and then fail on flush.
        languages = data.pop("languages", None)

        for field, value in data.items():
            setattr(profile, field, value)

        if languages is not None:
            self._apply_languages(profile, payload.languages or [])

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
        if not profile.photo_url:
            missing.append("talent.field.photo")
        if not (profile.phone or profile.whatsapp):
            missing.append("talent.field.contact")
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
            profile.headline,
            profile.bio,
            skill,
            location,
            profile.skills_text,
            profile.services_offered,
        )
