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
