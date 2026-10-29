"""Enumerations shared by models, schemas and services."""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"


class StaffRole(str, enum.Enum):
    """What an administrator account may do; see ``app/core/permissions.py``.

    Every ``ADMIN`` account carries one. A manager invites the rest and is
    the only one who can touch staff, exports, permanent deletes and the
    site's settings (the owners' decision, 26 Oct 2026).
    """

    MANAGER = "MANAGER"
    REVIEWER = "REVIEWER"
    SUPPORT = "SUPPORT"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


class BusinessStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class ImageKind(str, enum.Enum):
    LOGO = "LOGO"
    COVER = "COVER"
    GALLERY = "GALLERY"
    ITEM = "ITEM"


class LocationType(str, enum.Enum):
    GOVERNORATE = "GOVERNORATE"
    DISTRICT = "DISTRICT"
    TOWN = "TOWN"


class SocialPlatform(str, enum.Enum):
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"
    TIKTOK = "TIKTOK"
    YOUTUBE = "YOUTUBE"
    WHATSAPP = "WHATSAPP"
    WEBSITE = "WEBSITE"


class Currency(str, enum.Enum):
    USD = "USD"
    LBP = "LBP"


class ModerationActionType(str, enum.Enum):
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    SUSPEND = "SUSPEND"
    REACTIVATE = "REACTIVATE"


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class MaritalStatus(str, enum.Enum):
    SINGLE = "SINGLE"
    MARRIED = "MARRIED"
    DIVORCED = "DIVORCED"
    WIDOWED = "WIDOWED"


class LanguageProficiency(str, enum.Enum):
    """Ordered weakest to strongest; the order is what the profile renders."""

    BASIC = "BASIC"
    GOOD = "GOOD"
    FLUENT = "FLUENT"
    NATIVE = "NATIVE"


class FeedbackStatus(str, enum.Enum):
    """Kanban columns. Order matters for the board and for sensible sorting;
    keep new values here in the order they should appear left to right."""

    BACKLOG = "BACKLOG"
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class FeedbackPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class FeedbackAttachmentKind(str, enum.Enum):
    SCREENSHOT = "SCREENSHOT"
    PHOTO = "PHOTO"
    DOCUMENT = "DOCUMENT"


class VerificationDocumentKind(str, enum.Enum):
    """Which personal document a stored file is.

    ``IDENTITY`` and ``IDENTITY_BACK`` are the two sides of the ID card every
    owner uploads — separate kinds rather than two rows of one kind, because
    the table stores one document per owner per kind and a reviewer opening
    "the ID" means a specific side. ``CV`` is the résumé a talent profile may
    attach. All are admin-gated — the kind only says what the reviewer is
    looking at, never who may look.
    """

    IDENTITY = "IDENTITY"
    IDENTITY_BACK = "IDENTITY_BACK"
    CV = "CV"


class ViewSubject(str, enum.Enum):
    """What a counted view was a view *of*.

    The view counter is one table for all three, keyed by this plus an id,
    so a new surface needs no migration. The trade is that ``subject_id``
    carries no foreign key and cannot: it points at three different tables.
    Deletion therefore has to purge counters explicitly -- see
    ``ViewCounterService.forget`` -- rather than relying on ``ON DELETE``.
    Ids are UUIDv4, so a purge that is missed leaves dead rows and never
    misattributes a count to a later listing.
    """

    BUSINESS = "BUSINESS"
    TALENT = "TALENT"
    PRODUCT = "PRODUCT"


class TestimonialStatus(str, enum.Enum):
    """Where a piece of submitted praise is.

    Submitted text waits on an administrator (``PENDING_REVIEW``), whose
    approval publishes it (``APPROVED``); ``REJECTED`` is never shown.

    ``PENDING_OWNER`` and ``HIDDEN`` belong to the old two-gate design, in
    which the listing's owner also approved and could hide. The owners
    removed that step (round 3). Both values stay because Postgres cannot
    drop an enum value: nothing writes ``PENDING_OWNER`` any more (the
    migration returned those rows to review), and a row an owner hid before
    the change stays hidden until an administrator approves it.
    """

    PENDING_REVIEW = "PENDING_REVIEW"
    PENDING_OWNER = "PENDING_OWNER"
    APPROVED = "APPROVED"
    HIDDEN = "HIDDEN"
    REJECTED = "REJECTED"


class OrderStatus(str, enum.Enum):
    """How far the owner has got with an order request.

    Deliberately three states and no payment or fulfilment vocabulary: this
    is a request to be contacted, not a checkout. ``DONE`` means the owner
    is finished with the row, whatever happened -- sold, declined or the
    customer went quiet -- because a directory has no way to know which and
    should not pretend to.
    """

    NEW = "NEW"
    CONTACTED = "CONTACTED"
    DONE = "DONE"


class OwnerRelation(str, enum.Enum):
    """How the person listing a business stands to the establishment itself.

    A moderation signal rather than a public one: it answers "is this person
    entitled to list on behalf of this place", which is a reviewer's question.
    It therefore sits on ``OwnerBusinessOut`` and not on the public detail
    schema -- see ``tests/test_owner_relation.py``, which pins that boundary
    the way ``test_identity.py`` pins the account holder's own fields.

    Per *business*, not per account, because one person may own one
    establishment and manage another; that is exactly why it cannot live on
    ``users`` beside the identity fields it is asked for alongside.
    """

    OWNER = "OWNER"
    MANAGER = "MANAGER"
    WORKER = "WORKER"


class GoodsOrigin(str, enum.Enum):
    """Whether goods are made in the South or imported.

    Two separate doors on both the offering and the looking-for pages, at the
    CEO's request: a southern store selling imported goods is welcome, but a
    buyer looking for what the South itself produces must be able to tell the
    two apart. Carried by each *product*, so a shop selling both registers
    once and its goods appear under both doors; the shop's own mark is the
    door it came through and the default its new products take. Public,
    because it is exactly what a visitor filters on.
    """

    LOCAL = "LOCAL"
    IMPORTED = "IMPORTED"


class TalentKind(str, enum.Enum):
    """Which of the two directories a talent profile belongs to.

    The owners split «services and skills» in two: people who offer a
    service (a mechanic, a travel office, a teacher, a plumber) and people
    looking for a job. The owner of the profile chooses. Public, because it
    is which page the profile is listed on.
    """

    SERVICE = "SERVICE"
    JOB_SEEKER = "JOB_SEEKER"


class WorkMode(str, enum.Enum):
    """How a service is delivered. Public: visitors filter on it.

    Asked of everyone offering a service at the owners' request. ``BOTH``
    matches either filter, so a visitor looking for remote help still finds
    someone who also works in person.
    """

    REMOTE = "REMOTE"
    ON_SITE = "ON_SITE"
    BOTH = "BOTH"


class EmploymentType(str, enum.Enum):
    """What kind of job a talent profile is looking for, if anything."""

    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"


class ArticleSection(str, enum.Enum):
    """Which of the two "coming soon" nav pages a published article belongs to.

    ``BLOG`` is the professional-tips section (``/blog``), ``NEWS`` is
    activities-and-news (``/news``) — the two placeholders the top nav has
    linked to since before this content type existed.
    """

    BLOG = "BLOG"
    NEWS = "NEWS"


class ContactChannel(str, enum.Enum):
    """Which way a talent profile would rather be contacted.

    Optional, and not a restriction: every contact detail the person filled in
    stays on the page. It decides which one the page leads with, because a
    profile offering four ways to reach someone is really offering none —
    a visitor picks the first, which may be the one that is never answered.
    """

    PHONE = "PHONE"
    WHATSAPP = "WHATSAPP"
    EMAIL = "EMAIL"
    WEBSITE = "WEBSITE"


class ApplicationKind(str, enum.Enum):
    """Which public form an application came through."""

    BUSINESS = "BUSINESS"
    TALENT = "TALENT"


class WorkshopMode(str, enum.Enum):
    """Where a workshop happens: online (the link is sent after sign-up) or
    in person, in a town."""

    ONLINE = "ONLINE"
    IN_PERSON = "IN_PERSON"
