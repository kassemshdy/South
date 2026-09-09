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

    ``IDENTITY`` is the ID scan every owner uploads; ``CV`` is the résumé a
    talent profile may attach. Both are admin-gated — the kind only says what
    the reviewer is looking at, never who may look.
    """

    IDENTITY = "IDENTITY"
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
    """Where a piece of submitted praise is in the owner's hands.

    ``PENDING`` is invisible to everyone but the owner and an administrator.
    ``APPROVED`` is the only state a public payload may carry. ``HIDDEN`` is
    an owner taking one down again -- kept rather than deleted so the same
    text cannot be resubmitted and re-approved by accident, and so an
    administrator can still see what was published.
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    HIDDEN = "HIDDEN"


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
