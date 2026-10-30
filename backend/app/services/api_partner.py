"""API keys for the partner feed (Yalla Pay, AdsTalk).

A key is issued by a manager, shown once, and stored as its SHA-256 only --
the same promise as an owner's issued password. SHA-256 rather than bcrypt
because the key is 32 random bytes, not something a person chose: there is
nothing to brute-force, and the lookup runs on every partner request.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.integration import ApiPartner

KEY_PREFIX = "jnb_"
SCOPES = frozenset({"stores:read", "products:read"})
#: How stale ``last_used_at`` may get before a request writes it again.
TOUCH_EVERY = timedelta(minutes=5)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class ApiPartnerService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def all(self) -> list[ApiPartner]:
        return list(self._db.scalars(select(ApiPartner).order_by(ApiPartner.created_at.desc())))

    def get(self, partner_id: uuid.UUID) -> ApiPartner:
        partner = self._db.get(ApiPartner, partner_id)
        if partner is None:
            raise NotFoundError("partner_api.not_found")
        return partner

    def issue(
        self, name: str, scopes: list[str], created_by: uuid.UUID | None
    ) -> tuple[ApiPartner, str]:
        unknown = set(scopes) - SCOPES
        if unknown or not scopes:
            raise ValidationError("partner_api.bad_scope", code="bad_scope")
        key = KEY_PREFIX + secrets.token_urlsafe(32)
        partner = ApiPartner(
            name=name.strip(),
            key_prefix=key[:12],
            key_hash=hash_key(key),
            scopes=" ".join(sorted(set(scopes))),
            active=True,
            created_by=created_by,
        )
        self._db.add(partner)
        self._db.commit()
        return partner, key

    def rotate(self, partner: ApiPartner) -> str:
        """A new key; the old one stops working at once."""
        key = KEY_PREFIX + secrets.token_urlsafe(32)
        partner.key_prefix = key[:12]
        partner.key_hash = hash_key(key)
        partner.active = True
        self._db.commit()
        return key

    def revoke(self, partner: ApiPartner) -> None:
        partner.active = False
        self._db.commit()

    def authenticate(self, key: str) -> ApiPartner | None:
        if not key.startswith(KEY_PREFIX):
            return None
        partner = self._db.scalars(
            select(ApiPartner).where(ApiPartner.key_hash == hash_key(key))
        ).first()
        if partner is None or not partner.active:
            return None
        now = datetime.now(UTC)
        if partner.last_used_at is None or now - partner.last_used_at > TOUCH_EVERY:
            partner.last_used_at = now
            self._db.commit()
        return partner
