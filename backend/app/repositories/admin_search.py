"""Finding a listing by a phone number, for the admin lists.

``search_text`` holds names and descriptions, so a number typed into the
admin search found nothing, and the reviewers fell back to the browser's
own find on the one page loaded (the owners' ticket, 29 Oct 2026). A query
with enough digits in it is also matched against the listing's phone and
WhatsApp and the owner's sign-in number, compared as bare digits so
"03 123 456", "+961 3 123456" and "3123456" all find the same account.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import ColumnElement, exists, func, or_, select

from app.models.user import User

#: Fewer digits than this is a name with a number in it, not a phone.
MIN_DIGITS = 5


def phone_digits(q: str) -> str | None:
    """The query's digits without a country code or leading zero, or None."""
    digits = re.sub(r"\D", "", q)
    if len(digits) < MIN_DIGITS:
        return None
    for prefix in ("00961", "961"):
        if digits.startswith(prefix):
            digits = digits[len(prefix):]
            break
    digits = digits.lstrip("0")
    return digits if len(digits) >= MIN_DIGITS - 1 else None


def _digits_of(column: Any) -> ColumnElement[str]:
    return func.regexp_replace(func.coalesce(column, ""), "[^0-9]", "", "g")


def phone_match(digits: str, owner_id: Any, *columns: Any) -> ColumnElement[bool]:
    """The listing's own numbers, or its owner's sign-in number, contain these digits."""
    pattern = f"%{digits}%"
    owner = exists(
        select(User.id).where(User.id == owner_id, _digits_of(User.phone_number).like(pattern))
    )
    return or_(owner, *(_digits_of(column).like(pattern) for column in columns))

