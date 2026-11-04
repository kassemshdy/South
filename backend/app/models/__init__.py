"""SQLAlchemy models. Importing this package registers every table on Base."""

from app.models.activity import Activity, CarouselSlide
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
from app.models.integration import (
    ApiPartner,
    IntegrationOutbox,
    ItemLink,
    StoreLink,
)
from app.models.job import JobApplication, JobContactClickDaily, JobOpening
from app.models.open_service_request import OpenServiceRequest
from app.models.order import Order, OrderLine
from app.models.page import Page
from app.models.page_cover import PageCover
from app.models.partner import PartnerRequest
from app.models.reel import Reel
from app.models.service_request import ServiceRequest
from app.models.site_setting import SiteSetting
from app.models.story import StoryImage
from app.models.talent import (
    EmployerRequest,
    TalentCourse,
    TalentEducation,
    TalentExperience,
    TalentFaq,
    TalentImage,
    TalentModerationAction,
    TalentProfile,
    TalentServiceOffer,
    TalentSkill,
    TalentSocialLink,
    TalentWorkArea,
    TalentWorkTypeRow,
)
from app.models.taxonomy import Category, Location
from app.models.team import TeamMember
from app.models.testimonial import Testimonial
from app.models.user import User
from app.models.verification import OwnerVerificationDocument
from app.models.workshop import Workshop, WorkshopRegistration

__all__ = [
    "Activity",
    "ApiPartner",
    "Article",
    "ArticleSection",
    "Business",
    "BusinessDocument",
    "BusinessImage",
    "BusinessItem",
    "BusinessItemImage",
    "BusinessSocialLink",
    "BusinessStatus",
    "CarouselSlide",
    "Category",
    "Currency",
    "DiscardedApplication",
    "EmployerRequest",
    "FeedbackAttachment",
    "FeedbackAttachmentKind",
    "FeedbackComment",
    "FeedbackPriority",
    "FeedbackStatus",
    "FeedbackTicket",
    "ImageKind",
    "IntegrationOutbox",
    "ItemLink",
    "JobApplication",
    "JobContactClickDaily",
    "JobOpening",
    "ListingViewDaily",
    "Location",
    "LocationType",
    "ModerationAction",
    "ModerationActionType",
    "OpenServiceRequest",
    "Order",
    "OrderLine",
    "OrderStatus",
    "OwnerVerificationDocument",
    "Page",
    "PageCover",
    "PartnerRequest",
    "RateLimitEvent",
    "Reel",
    "ServiceRequest",
    "SiteSetting",
    "SocialPlatform",
    "StoreLink",
    "StoryImage",
    "TalentCourse",
    "TalentEducation",
    "TalentExperience",
    "TalentFaq",
    "TalentImage",
    "TalentModerationAction",
    "TalentProfile",
    "TalentServiceOffer",
    "TalentSkill",
    "TalentSocialLink",
    "TalentWorkArea",
    "TalentWorkTypeRow",
    "TeamMember",
    "Testimonial",
    "TestimonialStatus",
    "User",
    "UserRole",
    "ViewSubject",
    "Workshop",
    "WorkshopRegistration",
]
