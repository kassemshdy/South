"""Which staff role may do what in the admin area.

Every administrator account carries a ``StaffRole``. Rather than a check in
each of the admin routes, ``require_admin`` looks the route up here by its
method and path template, so the whole policy is one table to read and one
test (``tests/test_permissions.py``) to keep honest:

- every staff role may **read** the admin area (any GET), except the
  documents, export and staff list behind ``RESTRICTED_READS``;
- every **write** must be listed in ``WRITES``; one that is not is the
  manager's alone, so a new admin route is closed until someone decides who
  may use it, rather than open to every member of staff.

The owners' decisions (26 Oct 2026): reviewers moderate, support handles
tickets, orders and owners' passwords, content editors run the editorial
pages, viewers only look; staff, exports, permanent deletes and the site's
settings are the manager's.
"""

from __future__ import annotations

from app.models.enums import StaffRole

M = StaffRole.MANAGER
R = StaffRole.REVIEWER
S = StaffRole.SUPPORT
E = StaffRole.EDITOR

#: Reads closed to some staff: ID scans, CVs and a business's official
#: papers (reviewers and the manager), the export and the staff list (the
#: manager).
RESTRICTED_READS: dict[str, frozenset[StaffRole]] = {
    path: frozenset({M, R})
    for path in (
        "/api/admin/users/{user_id}/verification-document",
        "/api/admin/users/{user_id}/verification-document/download",
        "/api/admin/users/{user_id}/verification-document-back",
        "/api/admin/users/{user_id}/verification-document-back/download",
        "/api/admin/users/{user_id}/cv-document",
        "/api/admin/users/{user_id}/cv-document/download",
        "/api/admin/businesses/{business_id}/documents/{document_id}/download",
    )
} | {
    # A spreadsheet of every account's identity and every customer's phone.
    "/api/admin/export/{dataset}.csv": frozenset({M}),
    "/api/admin/staff": frozenset({M}),
    # Whoever may issue an owner's password may see whether theirs is current.
    "/api/admin/users/{user_id}/credentials": frozenset({M, R, S}),
}

_MODERATE = frozenset({M, R})
_SUPPORT = frozenset({M, S})
_CREDENTIALS = frozenset({M, R, S})
_CONTENT = frozenset({M, E})

WRITES: dict[tuple[str, str], frozenset[StaffRole]] = {
    # Moderation
    **{
        ("POST", f"/api/admin/businesses/{{business_id}}/{action}"): _MODERATE
        for action in (
            "approve",
            "reject",
            "suspend",
            "reactivate",
            "goods-origin",
            "images",
            "category",
            "place",
        )
    },
    ("DELETE", "/api/admin/businesses/{business_id}/items/{item_id}"): _MODERATE,
    **{
        ("POST", f"/api/admin/talent/{{profile_id}}/{action}"): _MODERATE
        for action in (
            "approve",
            "reject",
            "suspend",
            "reactivate",
            "skill",
            "place",
            "convert-to-business",
        )
    },
    # Owners' photo stories are reviewed like the listings they belong to.
    ("POST", "/api/admin/stories/{story_id}/approve"): _MODERATE,
    ("POST", "/api/admin/stories/{story_id}/reject"): _MODERATE,
    ("DELETE", "/api/admin/stories/{story_id}"): _MODERATE,
    ("POST", "/api/admin/testimonials/{testimonial_id}/approve"): _MODERATE,
    ("POST", "/api/admin/testimonials/{testimonial_id}/reject"): _MODERATE,
    ("DELETE", "/api/admin/testimonials/{testimonial_id}"): _MODERATE,
    # Owners' passwords: whoever approves, and whoever answers "I forgot".
    ("POST", "/api/admin/users/{user_id}/credentials"): _CREDENTIALS,
    # Support
    ("POST", "/api/admin/feedback/tickets"): _SUPPORT,
    ("PUT", "/api/admin/feedback/tickets/{ticket_id}"): _SUPPORT,
    ("DELETE", "/api/admin/feedback/tickets/{ticket_id}"): _SUPPORT,
    ("POST", "/api/admin/feedback/tickets/{ticket_id}/attachments"): _SUPPORT,
    ("DELETE", "/api/admin/feedback/tickets/{ticket_id}/attachments/{attachment_id}"): _SUPPORT,
    ("POST", "/api/admin/feedback/tickets/{ticket_id}/comments"): _SUPPORT,
    ("POST", "/api/admin/feedback/tickets/{ticket_id}/move"): _SUPPORT,
    ("POST", "/api/admin/discarded-applications/{application_id}/dismiss"): _SUPPORT,
    # Adds it to the account: deciding it is that person is a review call.
    ("POST", "/api/admin/discarded-applications/{application_id}/attach"): _MODERATE,
    ("DELETE", "/api/admin/partners/{request_id}"): _SUPPORT,
    ("POST", "/api/admin/partners/{request_id}/solve"): _SUPPORT,
    ("POST", "/api/admin/partners/{request_id}/reopen"): _SUPPORT,
    # Content
    ("POST", "/api/admin/articles"): _CONTENT,
    ("PUT", "/api/admin/articles/{article_id}"): _CONTENT,
    ("DELETE", "/api/admin/articles/{article_id}"): _CONTENT,
    ("POST", "/api/admin/articles/{article_id}/image"): _CONTENT,
    ("DELETE", "/api/admin/articles/{article_id}/image"): _CONTENT,
    ("POST", "/api/admin/articles/{article_id}/publish"): _CONTENT,
    ("POST", "/api/admin/articles/{article_id}/unpublish"): _CONTENT,
    ("POST", "/api/admin/page-covers/{page_key}"): _CONTENT,
    ("DELETE", "/api/admin/page-covers/{page_key}"): _CONTENT,
    # The home page's section order: the editorial pages' people.
    ("PUT", "/api/admin/home/layout"): _CONTENT,
    ("PUT", "/api/admin/pages/{key}"): _CONTENT,
    ("PUT", "/api/admin/team/{slot}"): _CONTENT,
    ("POST", "/api/admin/team/{slot}/photo"): _CONTENT,
    ("DELETE", "/api/admin/team/{slot}/photo"): _CONTENT,
    # The home page's Instagram reels.
    ("POST", "/api/admin/reels"): _CONTENT,
    ("PUT", "/api/admin/reels/order"): _CONTENT,
    ("PUT", "/api/admin/reels/{reel_id}"): _CONTENT,
    ("DELETE", "/api/admin/reels/{reel_id}"): _CONTENT,
    ("POST", "/api/admin/reels/{reel_id}/cover"): _CONTENT,
    ("DELETE", "/api/admin/reels/{reel_id}/cover"): _CONTENT,
    **{
        (method, path): _CONTENT
        for kind, key in (
            ("categories", "category_id"),
            ("locations", "location_id"),
            ("talent-skills", "skill_id"),
        )
        for method, path in (
            ("POST", f"/api/admin/{kind}"),
            ("PUT", f"/api/admin/{kind}/{{{key}}}"),
            ("DELETE", f"/api/admin/{kind}/{{{key}}}"),
        )
    },
    # The manager's alone, listed so the decision is visible rather than a
    # fall-through: permanent deletes, site settings, staff.
    ("DELETE", "/api/admin/businesses/{business_id}"): frozenset({M}),
    ("DELETE", "/api/admin/talent/{profile_id}"): frozenset({M}),
    ("DELETE", "/api/admin/users/{user_id}"): frozenset({M}),
    ("PUT", "/api/admin/site-settings"): frozenset({M}),
    ("POST", "/api/admin/staff"): frozenset({M}),
    ("PATCH", "/api/admin/staff/{user_id}"): frozenset({M}),
    ("POST", "/api/admin/staff/{user_id}/password"): frozenset({M}),
}

ALL_STAFF = frozenset(StaffRole)
MANAGER_ONLY = frozenset({M})


def allowed_roles(method: str, path: str) -> frozenset[StaffRole]:
    """Who may call this admin route. Unknown writes are the manager's."""
    if method in ("GET", "HEAD", "OPTIONS"):
        return RESTRICTED_READS.get(path, ALL_STAFF)
    return WRITES.get((method, path), MANAGER_ONLY)
