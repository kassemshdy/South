"""Enumerations shared by models, schemas and services."""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"


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
    """Where a piece of submitted praise is, across two gates.

    Submitted text waits on the platform first (``PENDING_REVIEW``), because
    handing abuse straight to the shop owner it was aimed at is the thing a
    review gate exists to prevent. Only what an administrator clears reaches
    the owner (``PENDING_OWNER``); only what the owner then approves is public
    (``APPROVED``). ``REJECTED`` never reaches the owner at all.

    Both gates are deliberate. The platform gate is about abuse, which is the
    platform's problem; the owner gate is what keeps this *selected praise*
    rather than a review system, and removing it would make a business unable
    to decline praise it knows to be untrue. ``HIDDEN`` is an owner taking a
    published one down again -- kept rather than deleted so the same text
    cannot be resubmitted and re-approved by accident, and so an administrator
    can still see what was once published.
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
    """Whether a business offers goods made in the South or imported ones.

    Two separate doors on both the offering and the looking-for pages, at the
    CEO's request: a southern store selling imported goods is welcome, but a
    buyer looking for what the South itself produces must be able to tell the
    two apart. Per *business*, chosen by the door the owner came through --
    one listing, one mark -- and public, because it is exactly what a visitor
    filters on.
    """

    LOCAL = "LOCAL"
    IMPORTED = "IMPORTED"


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
