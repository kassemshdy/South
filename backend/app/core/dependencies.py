"""FastAPI dependencies: request context, authentication and authorization.

Authorization is enforced here and in services — never by trusting the frontend.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth.otp.base import OtpProvider
from app.auth.otp.factory import get_otp_provider
from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError, NotFoundError, PermissionDeniedError
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.business import Business
from app.models.enums import UserRole
from app.models.talent import TalentProfile
from app.models.user import User
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository
from app.repositories.user import UserRepository

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
OtpProviderDep = Annotated[OtpProvider, Depends(get_otp_provider)]


def get_client_ip(request: Request) -> str | None:
    """Client IP, honouring the proxy header set by Railway/Caddy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
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
    return user


def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    if user is None:
        raise AuthenticationError()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
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


def require_admin(user: CurrentUser) -> User:
    if user.role is not UserRole.ADMIN:
        raise PermissionDeniedError("auth.admin_only")
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
