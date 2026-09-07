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
