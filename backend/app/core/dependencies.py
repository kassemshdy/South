"""FastAPI dependencies: request context, authentication and authorization.

Authorization is enforced here and in services — never by trusting the frontend.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError, NotFoundError, PermissionDeniedError
from app.core.permissions import VIEW_AS_ROLES, allowed_roles
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.business import Business
from app.models.enums import StaffRole, UserRole
from app.models.talent import TalentProfile
from app.models.user import User
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository
from app.repositories.user import UserRepository
from app.services.telegram_archive import SESSION_ACTOR as ARCHIVE_ACTOR
from app.services.telegram_archive import person as archive_person

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_client_ip(request: Request, settings: AppSettings) -> str | None:
    """The caller's address, read from the *right* of ``X-Forwarded-For``.

    ``X-Forwarded-For`` is a chain: each proxy appends the address it saw, so
    the entries at the right are the ones our own infrastructure added and the
    entries at the left are whatever the original client sent -- which anyone
    can forge. Reading the left-most entry (the previous implementation) let a
    caller set ``X-Forwarded-For: 1.2.3.4`` and be rate-limited as ``1.2.3.4``,
    a fresh identity per request and so no limit at all on the anonymous write
    endpoints (registration, testimonials, orders, service requests).

    ``TRUSTED_PROXY_HOPS`` says how many entries at the right our proxies own;
    the real client is that many places from the end, and nothing to its left
    is ever trusted. With no header, or fewer entries than expected, we fall
    back to the socket peer -- correct for a direct connection in development.
    """
    hops = settings.trusted_proxy_hops
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and hops > 0:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if len(parts) >= hops:
            return parts[-hops]
    return request.client.host if request.client else None


ClientIp = Annotated[str | None, Depends(get_client_ip)]


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


#: Methods a read-only view may use: reading changes nothing.
_READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _enforce_view_only(request: Request, db: DbSession, payload: dict[str, object]) -> None:
    """An administrator looking at an owner's account, read-only.

    The token is the owner's (so every owner route answers exactly as it
    would for them) and carries the administrator's id and token version.
    It stops working the moment either side's sessions are revoked, or the
    administrator loses a role that may use it, and whatever it asks to
    change is refused here, before any route runs: the read-only rule lives
    on the server, not in which buttons the page hides.
    """
    try:
        admin_id = uuid.UUID(str(payload.get("va")))
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("auth.session.invalid", code="invalid_token") from exc
    admin = UserRepository(db).get_active(admin_id)
    if (
        admin is None
        or admin.role is not UserRole.ADMIN
        or (admin.staff_role or StaffRole.VIEWER) not in VIEW_AS_ROLES
        or int(str(payload.get("atv", -1))) != admin.token_version
    ):
        raise AuthenticationError("auth.session.expired", code="token_revoked")
    if request.method not in _READ_METHODS:
        raise PermissionDeniedError("auth.view_only", code="view_only")


def get_current_user_optional(request: Request, db: DbSession) -> User | None:
    """Resolve the caller when a valid token is present, else None."""
    token = _bearer_token(request)
    if token is None:
        return None

    payload = decode_access_token(token)
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("auth.session.invalid", code="invalid_token") from exc

    user = UserRepository(db).get_active(user_id)
    if user is None:
        raise AuthenticationError("auth.account.unavailable", code="account_disabled")

    # Token version lets us revoke every session issued to a user.
    if int(payload.get("tv", -1)) != user.token_version:
        raise AuthenticationError("auth.session.expired", code="token_revoked")
    if payload.get("va") is not None:
        _enforce_view_only(request, db, payload)
    # Who is saving, for the Telegram archive, which skips administrators.
    db.info[ARCHIVE_ACTOR] = (user.role.value, *archive_person(user))
    return user


def get_signed_in_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    """The caller, whatever state their account is in.

    Used only by the two routes an account with an issued password may still
    reach: reading itself, and replacing that password. Everything else goes
    through ``get_current_user`` below.
    """
    if user is None:
        raise AuthenticationError()
    return user


def get_current_user(
    user: Annotated[User, Depends(get_signed_in_user)],
) -> User:
    """The caller, refused while an issued password has not been replaced.

    Nothing sets the flag any more: the owners decided an issued password is
    the owner's to keep, with the WhatsApp message as their record of it
    (migration d7a1c4e9b305 cleared it on the accounts that carried it). The
    check stays so that setting it again shuts every owner route in one
    place, with a new owner endpoint covered by default.
    """
    if user.must_change_password:
        raise PermissionDeniedError(
            "auth.password_change_required", code="password_change_required"
        )
    return user


def get_listing_owner(user: CurrentUser) -> User:
    """The caller, refused if they are an administrator.

    An administrator decides whether a listing may be published. Owning one
    puts them on both sides of that decision, so the two create routes are
    shut to them — not hidden in the interface and open at the API, which is
    a rule in name only.

    Deliberately narrow: an administrator still reads, moderates and edits
    everything they could before. What they cannot do is bring a listing of
    their own into the queue they judge.
    """
    if user.role is UserRole.ADMIN:
        raise PermissionDeniedError("listing.admin_cannot_own", code="admin_account")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
ListingOwner = Annotated[User, Depends(get_listing_owner)]
SignedInUser = Annotated[User, Depends(get_signed_in_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]


def get_viewer(request: Request, db: DbSession) -> User | None:
    """The caller if they can be identified, and None if they cannot.

    Distinct from ``get_current_user_optional``, which returns None only for
    a request carrying *no* token and raises 401 for one carrying a bad one.
    That is right wherever a supplied token has to be honest, and wrong on a
    public page: the frontend attaches whatever token is in local storage to
    every request, so an expired or revoked session would turn the public
    business, talent and product pages into 401s for a visitor who is simply
    browsing. Verified before this existed -- a public listing answered 401
    to `Bearer not-a-real-token`.

    So identity here is a nicety, not a credential. It is used for one
    thing: not counting a view when the person looking is the listing's own
    owner. A token we cannot make sense of means we do not know who this
    is, which is exactly what None says.
    """
    try:
        return get_current_user_optional(request, db)
    except AuthenticationError:
        return None


Viewer = Annotated[User | None, Depends(get_viewer)]


def is_crawler_request(request: Request) -> bool:
    """Whether the caller is a search crawler or link-preview fetcher, so a
    public page is not counted as a view. The user agent is read, never kept."""
    from app.services.analytics import is_crawler

    return is_crawler(request.headers.get("user-agent"))


Crawler = Annotated[bool, Depends(is_crawler_request)]


def require_admin(request: Request, user: CurrentUser) -> User:
    """An administrator whose staff role may use this route.

    The route is looked up in ``app/core/permissions.py`` by its method and
    path template, so this one check enforces the whole staff policy. An
    administrator with no role recorded is treated as a viewer: the
    migration that introduced roles made every existing one a manager, so
    only an account created some other way lands here, and it gets the
    least.
    """
    if user.role is not UserRole.ADMIN:
        raise PermissionDeniedError("auth.admin_only")
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    role = user.staff_role or StaffRole.VIEWER
    if role not in allowed_roles(request.method, path):
        raise PermissionDeniedError("auth.staff_role_forbidden", code="staff_role_forbidden")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def require_owned_business(business_id: uuid.UUID, db: DbSession, user: CurrentUser) -> Business:
    """Load a business the caller owns.

    Returns 404 rather than 403 for someone else's business so the endpoint does
    not confirm that an id exists to a user who has no business with it.
    Administrators are intentionally *not* granted owner powers here; they act
    through the admin API, which records a moderation trail.
    """
    business = BusinessRepository(db).get_with_relations(business_id)
    if business is None or business.owner_id != user.id:
        raise NotFoundError("business.not_found")
    return business


OwnedBusiness = Annotated[Business, Depends(require_owned_business)]


def require_own_talent_profile(db: DbSession, user: CurrentUser) -> TalentProfile:
    """Load the caller's own talent profile.

    There is no profile id in the path: a profile is one-per-account, so the
    authenticated user *is* the lookup key and no request-supplied id can be
    used to reach someone else's profile.
    """
    profile = TalentRepository(db).get_for_owner(user.id)
    if profile is None:
        raise NotFoundError("talent.not_found")
    return profile


OwnTalentProfile = Annotated[TalentProfile, Depends(require_own_talent_profile)]
