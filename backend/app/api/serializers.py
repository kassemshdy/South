"""Model → schema conversion.

Kept in one module so the rule "public payloads never contain moderation fields
or the owner's login phone" is visible in a single place.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from app.core.pagination import Page
from app.models.business import Business, BusinessItem
from app.models.enums import ImageKind
from app.models.feedback import FeedbackAttachment, FeedbackComment, FeedbackTicket
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Category, Location
from app.models.user import User
from app.schemas.business import (
    BusinessDetailOut,
    BusinessImageOut,
    BusinessSummaryOut,
    OwnerBusinessOut,
    SocialLinkOut,
)
from app.schemas.common import PageMeta, PaginatedResponse
from app.schemas.feedback import (
    FeedbackAttachmentOut,
    FeedbackCommentOut,
    FeedbackSubmissionOut,
    FeedbackTicketDetailOut,
    FeedbackTicketSummaryOut,
    FeedbackUserOut,
)
from app.schemas.identity import OwnerIdentityOut
from app.schemas.item import BusinessItemOut
from app.schemas.moderation import (
    AdminBusinessOut,
    AdminTalentOut,
    AdminUserDetailOut,
    AdminUserOut,
    ModerationActionOut,
)
from app.schemas.product import ProductBusinessRef, ProductDetailOut, ProductSummaryOut
from app.schemas.talent import (
    OwnerTalentOut,
    TalentDetailOut,
    TalentImageOut,
    TalentLanguageOut,
    TalentSkillOut,
    TalentSummaryOut,
)
from app.schemas.taxonomy import CategoryOut, LocationOut

RecordT = TypeVar("RecordT")
SchemaT = TypeVar("SchemaT")


def category_out(category: Category | None, *, business_count: int = 0) -> CategoryOut | None:
    if category is None:
        return None
    data = CategoryOut.model_validate(category)
    return data.model_copy(update={"business_count": business_count})


def location_out(location: Location | None, *, business_count: int = 0) -> LocationOut | None:
    if location is None:
        return None
    data = LocationOut.model_validate(location)
    return data.model_copy(update={"business_count": business_count})


def item_out(item: BusinessItem) -> BusinessItemOut:
    return BusinessItemOut.model_validate(item)


def _gallery(business: Business) -> list[BusinessImageOut]:
    return [
        BusinessImageOut.model_validate(image)
        for image in sorted(business.images, key=lambda i: i.sort_order)
        if image.kind is ImageKind.GALLERY
    ]


def business_summary(business: Business) -> BusinessSummaryOut:
    return BusinessSummaryOut(
        id=business.id,
        name=business.name,
        slug=business.slug,
        short_description=business.short_description,
        logo_url=business.logo_url,
        cover_url=business.cover_url,
        phone=business.phone,
        whatsapp=business.whatsapp,
        category=category_out(business.category),
        custom_category_text=business.custom_category_text,
        location=location_out(business.location),
        created_at=business.created_at,
    )


def business_detail(business: Business) -> BusinessDetailOut:
    """Public profile. Contains only what the owner chose to publish."""
    return BusinessDetailOut(
        **business_summary(business).model_dump(),
        description=business.description,
        institution_name=business.institution_name,
        founding_date=business.founding_date,
        production_nature=business.production_nature,
        email=business.email,
        website=business.website,
        address_text=business.address_text,
        latitude=float(business.latitude) if business.latitude is not None else None,
        longitude=float(business.longitude) if business.longitude is not None else None,
        maps_url=business.maps_url,
        images=_gallery(business),
        social_links=[SocialLinkOut.model_validate(link) for link in business.social_links],
        items=[item_out(item) for item in sorted(business.items, key=lambda i: i.sort_order)],
        approved_at=business.approved_at,
    )


def owner_business(business: Business) -> OwnerBusinessOut:
    """Owner's own view — adds moderation state and the rejection reason."""
    return OwnerBusinessOut(
        **business_detail(business).model_dump(),
        status=business.status,
        rejection_reason=business.rejection_reason,
        submitted_at=business.submitted_at,
        updated_at=business.updated_at,
    )


def admin_business(business: Business) -> AdminBusinessOut:
    """Review payload — administrators may see the owner's account details."""
    return AdminBusinessOut(
        **owner_business(business).model_dump(),
        owner_id=business.owner_id,
        owner_phone=business.owner.phone_number if business.owner else None,
        owner_personal_phone=business.owner.personal_phone_number if business.owner else None,
        owner_identity=owner_identity(business.owner),
        owner_has_verification_document=bool(
            business.owner and business.owner.verification_document is not None
        ),
        owner_has_cv_document=bool(
            business.owner and business.owner.cv_document is not None
        ),
        owner_display_name=business.owner.display_name if business.owner else None,
        moderation_actions=[
            ModerationActionOut.model_validate(action)
            for action in sorted(business.moderation_actions, key=lambda a: a.created_at)
        ],
    )


def _product_business_ref(business: Business) -> ProductBusinessRef:
    return ProductBusinessRef(
        name=business.name,
        slug=business.slug,
        phone=business.phone,
        whatsapp=business.whatsapp,
        category=category_out(business.category),
        location=location_out(business.location),
    )


def product_summary(item: BusinessItem) -> ProductSummaryOut:
    return ProductSummaryOut(
        id=item.id,
        slug=item.slug,
        title=item.title,
        price=item.price,
        currency=item.currency,
        image_url=item.image_url,
        business=_product_business_ref(item.business),
    )


def product_detail(item: BusinessItem) -> ProductDetailOut:
    return ProductDetailOut(
        **product_summary(item).model_dump(),
        description=item.description,
        created_at=item.created_at,
    )


def talent_skill_out(skill: TalentSkill | None, *, talent_count: int = 0) -> TalentSkillOut | None:
    if skill is None:
        return None
    data = TalentSkillOut.model_validate(skill)
    return data.model_copy(update={"talent_count": talent_count})


def _talent_gallery(profile: TalentProfile) -> list[TalentImageOut]:
    return [
        TalentImageOut.model_validate(image)
        for image in sorted(profile.images, key=lambda i: i.sort_order)
        if image.kind is ImageKind.GALLERY
    ]


def talent_summary(profile: TalentProfile) -> TalentSummaryOut:
    return TalentSummaryOut(
        id=profile.id,
        display_name=profile.display_name,
        slug=profile.slug,
        headline=profile.headline,
        photo_url=profile.photo_url,
        phone=profile.phone,
        whatsapp=profile.whatsapp,
        years_experience=profile.years_experience,
        skill=talent_skill_out(profile.skill),
        custom_skill_text=profile.custom_skill_text,
        location=location_out(profile.location),
        created_at=profile.created_at,
    )


def talent_detail(profile: TalentProfile) -> TalentDetailOut:
    """Public profile. Contains only what the person chose to publish.

    Note what is *not* here: the owner's legal name, birth year, gender,
    marital status and civil-record places. Those describe the person rather
    than the work, belong to the account, and reach an administrator only
    through :func:`owner_identity`.
    """
    return TalentDetailOut(
        **talent_summary(profile).model_dump(),
        bio=profile.bio,
        email=profile.email,
        website=profile.website,
        images=_talent_gallery(profile),
        approved_at=profile.approved_at,
        highest_degree=profile.highest_degree,
        specialization=profile.specialization,
        university=profile.university,
        experience=profile.experience,
        skills_text=profile.skills_text,
        services_offered=profile.services_offered,
        languages=[
            TalentLanguageOut.model_validate(language)
            for language in sorted(profile.languages, key=lambda item: item.sort_order)
        ],
    )


def owner_talent(profile: TalentProfile) -> OwnerTalentOut:
    """Owner's own view — the public profile plus its moderation state."""
    return OwnerTalentOut(
        **talent_detail(profile).model_dump(),
        status=profile.status,
        rejection_reason=profile.rejection_reason,
        submitted_at=profile.submitted_at,
        updated_at=profile.updated_at,
    )


def owner_identity(user: User | None) -> OwnerIdentityOut | None:
    """The account holder's identity, for a review payload.

    Returns ``None`` rather than an all-null block when nothing has been
    filled in, so a reviewer can tell "not provided" from "provided empty".
    """
    if user is None:
        return None
    identity = OwnerIdentityOut.model_validate(user)
    if not identity.model_dump(exclude_none=True):
        return None
    return identity


def admin_talent(profile: TalentProfile) -> AdminTalentOut:
    """Review payload — administrators may see the account's own details."""
    return AdminTalentOut(
        **owner_talent(profile).model_dump(),
        owner_id=profile.owner_id,
        owner_phone=profile.owner.phone_number if profile.owner else None,
        owner_personal_phone=profile.owner.personal_phone_number if profile.owner else None,
        owner_identity=owner_identity(profile.owner),
        owner_has_verification_document=bool(
            profile.owner and profile.owner.verification_document is not None
        ),
        owner_has_cv_document=bool(
            profile.owner and profile.owner.cv_document is not None
        ),
        owner_display_name=profile.owner.display_name if profile.owner else None,
        moderation_actions=[
            ModerationActionOut.model_validate(action)
            for action in sorted(profile.moderation_actions, key=lambda a: a.created_at)
        ],
    )


def feedback_user_out(user: User | None) -> FeedbackUserOut | None:
    if user is None:
        return None
    return FeedbackUserOut.model_validate(user)


def feedback_attachment_out(attachment: FeedbackAttachment) -> FeedbackAttachmentOut:
    return FeedbackAttachmentOut.model_validate(attachment)


def feedback_comment_out(comment: FeedbackComment) -> FeedbackCommentOut:
    return FeedbackCommentOut(
        id=comment.id,
        body=comment.body,
        author_id=comment.author_id,
        author_display_name=comment.author.display_name if comment.author else None,
        created_at=comment.created_at,
    )


def feedback_submission(ticket: FeedbackTicket) -> FeedbackSubmissionOut:
    """The receipt for a reported problem -- and nothing else about the board.

    Built field by field rather than from the model, so adding a column to
    FeedbackTicket can never quietly widen what a reporter is shown.
    """
    return FeedbackSubmissionOut(
        id=ticket.id,
        title=ticket.title,
        created_at=ticket.created_at,
    )


def feedback_ticket_summary(ticket: FeedbackTicket) -> FeedbackTicketSummaryOut:
    return FeedbackTicketSummaryOut(
        id=ticket.id,
        title=ticket.title,
        status=ticket.status,
        priority=ticket.priority,
        sort_order=ticket.sort_order,
        reporter=FeedbackUserOut.model_validate(ticket.reporter),
        assignee=feedback_user_out(ticket.assignee),
        github_issue_number=ticket.github_issue_number,
        attachment_count=len(ticket.attachments),
        comment_count=len(ticket.comments),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def feedback_ticket_detail(ticket: FeedbackTicket) -> FeedbackTicketDetailOut:
    return FeedbackTicketDetailOut(
        **feedback_ticket_summary(ticket).model_dump(),
        description=ticket.description,
        page_path=ticket.page_path,
        client_context=ticket.client_context,
        resolved_at=ticket.resolved_at,
        attachments=[feedback_attachment_out(a) for a in ticket.attachments],
        comments=[feedback_comment_out(c) for c in ticket.comments],
    )


def admin_user(user: User, *, business_count: int = 0) -> AdminUserOut:
    data = AdminUserOut.model_validate(user)
    # Set explicitly: the identity columns sit on the user itself, so
    # model_validate has no nested attribute to build the block from.
    return data.model_copy(
        update={"business_count": business_count, "identity": owner_identity(user)}
    )


def admin_user_detail(
    user: User, *, businesses: list[Business], talent_profile: TalentProfile | None
) -> AdminUserDetailOut:
    base = admin_user(user, business_count=len(businesses))
    return AdminUserDetailOut(
        **base.model_dump(),
        businesses=[admin_business(business) for business in businesses],
        talent_profile=admin_talent(talent_profile) if talent_profile else None,
    )


def paginate(
    page: Page[RecordT], mapper: Callable[[RecordT], SchemaT]
) -> PaginatedResponse[SchemaT]:
    return PaginatedResponse(
        items=[mapper(item) for item in page.items],
        meta=PageMeta(
            total=page.total,
            page=page.page,
            page_size=page.page_size,
            total_pages=page.total_pages,
            has_next=page.has_next,
            has_previous=page.has_previous,
        ),
    )
