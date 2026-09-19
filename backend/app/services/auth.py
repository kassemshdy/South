"""Authentication: a phone number or an email address, and a password.

One way in, for everybody. An owner types the phone number their account is
keyed by, an administrator types their email address, and both arrive at
:meth:`AuthService.login`, which tells them apart by the shape of what was
typed and answers every failure identically.

There used to be a second way — a one-time code sent over SMS or WhatsApp —
and it is gone rather than disabled. No gateway was ever obtainable, so the
only provider that ever ran was the development one, which issues a fixed
code: on a deployment that is not a login, it is a way in for anyone who knows
a phone number. Deleting it is the fix. The account is still keyed by phone
number, so a gateway arriving later adds a door onto the same accounts.

A password an administrator issued is a way in exactly once — see
``must_change_password``.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AuthenticationError, RateLimitedError, ValidationError
from app.core.passwords import generate_temporary_password
from app.core.phone import normalize_phone
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._users = UserRepository(db)
        self._limiter = DatabaseRateLimiter(db)

        # A password is now the only thing standing between a stranger and
        # an account — there is no second factor and no code that expires — so
        # how many guesses fit in the window is the whole of the protection.
        # Keyed on the identifier someone typed, for the reason recorded
        # beside the setting itself.
        self._login_rule = RateLimitRule(
            bucket="password_login",
            limit=settings.password_login_limit,
            window_seconds=settings.password_login_window_seconds,
        )

    # --- Administrators ----------------------------------------------------

    def login_admin(self, email: str, password: str) -> tuple[User, str, datetime]:
        """The administrators-only door, kept beside the one everybody uses.

        :meth:`login` already signs an administrator in, so this is not the
        way in — it is the way in when the other one is broken. An
        administrator locked out of a deployment cannot ask anyone to let them
        back in, because they are who that request would go to.

        Same error and roughly the same work for an unknown address, a wrong
        password and a non-administrator account, so it does not enumerate
        administrators, and the same guess budget as :meth:`login`, so it is
        not the cheaper of the two to attack.
        """
        identifier = email.strip().lower()

        status = self._limiter.check(self._login_rule, identifier)
        if not status.allowed:
            raise RateLimitedError(status.retry_after_seconds, "auth.login.rate_limited")

        user = self._users.get_by_email(identifier)

        if user is None or not verify_password(password, user.password_hash):
            self._record_failed_login(identifier)
            logger.warning("Failed admin login", extra={"email": identifier})
            raise AuthenticationError(
                "auth.invalid_credentials", code="invalid_credentials"
            )
        if user.role is not UserRole.ADMIN or not user.is_active:
            self._record_failed_login(identifier)
            logger.warning("Non-admin attempted admin login", extra={"user_id": str(user.id)})
            raise AuthenticationError(
                "auth.invalid_credentials", code="invalid_credentials"
            )

        token, expires_at = create_access_token(
            user_id=user.id, role=user.role.value, token_version=user.token_version
        )
        return user, token, expires_at

    def login(
        self, identifier: str, password: str, *, client_ip: str | None = None
    ) -> tuple[User, str, datetime]:
        """Sign anybody in: a phone number or an email address, and a password.

        One method rather than one per role, because the form is one form. An
        owner knows their phone number and an administrator knows their email
        address, and asking which of the two someone is before they have
        proved who they are is a question with no useful answer — so the
        shape of what they typed picks the lookup, and everything after it is
        identical.

        Identical is the point. One error for every failure — unknown number,
        unknown address, wrong password, disabled account, an account that has
        no password yet — so the endpoint cannot be used to discover which
        numbers or addresses have accounts. An account with no password set,
        which is how every account starts before an administrator issues one,
        fails here too, because ``verify_password`` refuses a null hash.

        The budget is checked before anything is looked up, so it applies to
        an identifier with no account as well; spending it only on real
        accounts would make the difference measurable. Only *failures* are
        recorded, so signing in correctly never uses it up, and a run of wrong
        guesses ages out of the window on its own.
        """
        normalized = self._normalize_identifier(identifier)

        # A budget is only spendable on something storable, and an identifier
        # that normalizes to nothing is neither an account nor a guess at one.
        if normalized is None:
            raise AuthenticationError(
                "auth.invalid_credentials", code="invalid_credentials"
            )

        status = self._limiter.check(self._login_rule, normalized)
        if not status.allowed:
            raise RateLimitedError(status.retry_after_seconds, "auth.login.rate_limited")

        user = (
            self._users.get_by_email(normalized)
            if "@" in normalized
            else self._users.get_by_phone(normalized)
        )

        if user is None or not verify_password(password, user.password_hash):
            self._record_failed_login(normalized)
            logger.warning(
                "Failed sign-in", extra={"identifier": normalized, "request_ip": client_ip}
            )
            raise AuthenticationError(
                "auth.invalid_credentials", code="invalid_credentials"
            )
        if not user.is_active:
            self._record_failed_login(normalized)
            logger.warning(
                "Sign-in refused for a disabled account", extra={"user_id": str(user.id)}
            )
            raise AuthenticationError(
                "auth.invalid_credentials", code="invalid_credentials"
            )

        token, expires_at = create_access_token(
            user_id=user.id, role=user.role.value, token_version=user.token_version
        )
        return user, token, expires_at

    @staticmethod
    def _normalize_identifier(identifier: str) -> str | None:
        """The canonical form of what someone typed, or None if it is neither.

        An "@" is what tells the two apart, because no Lebanese number
        contains one and every email address does. Returning None rather than
        raising keeps a malformed entry indistinguishable from a wrong
        password: a 422 on "not a phone number" and a 401 on "wrong password"
        would together say which numbers are well formed, and the client
        already checks the shape before sending.
        """
        candidate = identifier.strip()
        if not candidate:
            return None
        if "@" in candidate:
            return candidate.lower()
        try:
            return normalize_phone(candidate)
        except ValidationError:
            return None

    def _record_failed_login(self, identifier: str) -> None:
        """Spend one guess, and commit it before the failure is raised.

        The commit is the point. The limiter only flushes, and the request
        that is about to raise never reaches a commit of its own — so without
        this the attempt is rolled back with the error and the budget never
        goes down, which is the whole of the protection.
        """
        self._limiter.hit(self._login_rule, identifier)
        self._db.commit()

    def set_password(self, user: User, password: str) -> None:
        """Replace the account's password and end every other session.

        Bumping ``token_version`` invalidates tokens issued before this point,
        which is the whole value of the change when the old password went out
        over WhatsApp: whoever else read that chat is signed out.
        """
        user.password_hash = hash_password(password)
        user.must_change_password = False
        user.token_version += 1
        self._db.commit()
        logger.info("Password changed", extra={"user_id": str(user.id)})

    def issue_password(self, user: User) -> str:
        """Generate a password for ``user`` and return it once.

        The plaintext is returned to the caller and never stored, logged or
        sent anywhere by this application — an administrator relays it over
        their own WhatsApp. It is a way in exactly once: `must_change_password`
        blocks every owner route until it has been replaced.
        """
        password = generate_temporary_password()
        user.password_hash = hash_password(password)
        user.must_change_password = True
        # Any session opened with a previous password stops here.
        user.token_version += 1
        self._db.commit()
        logger.info("Password issued to account", extra={"user_id": str(user.id)})
        return password
