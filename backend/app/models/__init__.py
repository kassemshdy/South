"""SQLAlchemy models. Importing this package registers every table on Base."""

from app.models.analytics import ListingViewDaily
from app.models.auth import OtpRequest, RateLimitEvent
from app.models.business import (
    Business,
    BusinessImage,
    BusinessItem,
    BusinessSocialLink,
    ModerationAction,
)
from app.models.enums import (
    BusinessStatus,
    Currency,
    FeedbackAttachmentKind,
    FeedbackPriority,
    FeedbackStatus,
    ImageKind,
    LocationType,
    ModerationActionType,
    OrderStatus,
    SocialPlatform,
    TestimonialStatus,
    UserRole,
    ViewSubject,
)
from app.models.feedback import FeedbackAttachment, FeedbackComment, FeedbackTicket
from app.models.order import Order, OrderLine
from app.models.service_request import ServiceRequest
from app.models.talent import (
    TalentImage,
    TalentModerationAction,
    TalentProfile,
    TalentSkill,
)
from app.models.taxonomy import Category, Location
from app.models.testimonial import Testimonial
from app.models.user import User
from app.models.verification import OwnerVerificationDocument

__all__ = [
    "Business",
    "BusinessImage",
    "BusinessItem",
    "BusinessSocialLink",
    "BusinessStatus",
    "Category",
    "Currency",
    "FeedbackAttachment",
    "FeedbackAttachmentKind",
    "FeedbackComment",
    "FeedbackPriority",
    "FeedbackStatus",
    "FeedbackTicket",
    "ImageKind",
    "ListingViewDaily",
    "Location",
    "LocationType",
    "ModerationAction",
    "ModerationActionType",
    "Order",
    "OrderLine",
    "OrderStatus",
    "OtpRequest",
    "OwnerVerificationDocument",
    "RateLimitEvent",
    "ServiceRequest",
    "SocialPlatform",
    "TalentImage",
    "TalentModerationAction",
    "TalentProfile",
    "TalentSkill",
    "Testimonial",
    "TestimonialStatus",
    "User",
    "UserRole",
    "ViewSubject",
]
