"""SQLAlchemy models. Importing this package registers every table on Base."""

from app.models.analytics import ListingViewDaily
from app.models.application import DiscardedApplication
from app.models.article import Article
from app.models.auth import RateLimitEvent
from app.models.business import (
    Business,
    BusinessDocument,
    BusinessImage,
    BusinessItem,
    BusinessItemImage,
    BusinessSocialLink,
    ModerationAction,
)
from app.models.enums import (
    ArticleSection,
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
    TalentSocialLink,
)
from app.models.taxonomy import Category, Location
from app.models.testimonial import Testimonial
from app.models.user import User
from app.models.verification import OwnerVerificationDocument

__all__ = [
    "Article",
    "ArticleSection",
    "Business",
    "BusinessDocument",
    "BusinessImage",
    "BusinessItem",
    "BusinessItemImage",
    "BusinessSocialLink",
    "BusinessStatus",
    "Category",
    "Currency",
    "DiscardedApplication",
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
    "OwnerVerificationDocument",
    "RateLimitEvent",
    "ServiceRequest",
    "SocialPlatform",
    "TalentImage",
    "TalentModerationAction",
    "TalentProfile",
    "TalentSkill",
    "TalentSocialLink",
    "Testimonial",
    "TestimonialStatus",
    "User",
    "UserRole",
    "ViewSubject",
]
