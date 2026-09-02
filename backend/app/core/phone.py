"""Lebanese phone number normalization.

Users type numbers many ways — 03 123 456, 3123456, 00961..., +961... — and all
of them must resolve to one canonical E.164 string so that "the same phone" is
one account.
"""

from __future__ import annotations

import re

from app.core.errors import ValidationError

LEBANON_COUNTRY_CODE = "961"

# Lebanese subscriber numbers are 7 digits (landline and older mobile) or
# 8 digits (mobile prefixes such as 76/78/79/81 with a leading digit).
_SUBSCRIBER_RE = re.compile(r"^[1-9]\d{6,7}$")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize_phone(raw: str) -> str:
    """Return ``+961XXXXXXXX``, raising ValidationError when unusable.

    Accepts Arabic-Indic digits, spaces, dashes, parentheses, a leading 0,
    a 00961 prefix or a +961 prefix.
    """
    if not raw or not raw.strip():
        raise ValidationError("رقم الهاتف مطلوب.", code="invalid_phone")

    digits = raw.translate(_ARABIC_DIGITS)
    digits = re.sub(r"[^\d+]", "", digits)

    if digits.startswith("+"):
        digits = digits[1:]
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith(LEBANON_COUNTRY_CODE):
        digits = digits[len(LEBANON_COUNTRY_CODE) :]
    # Local trunk prefix, e.g. 03 123 456.
    if digits.startswith("0"):
        digits = digits[1:]

    if not _SUBSCRIBER_RE.match(digits):
        raise ValidationError(
            "رقم الهاتف غير صالح. أدخل رقماً لبنانياً مثل 03123456.",
            code="invalid_phone",
        )

    return f"+{LEBANON_COUNTRY_CODE}{digits}"


def is_valid_phone(raw: str) -> bool:
    try:
        normalize_phone(raw)
    except ValidationError:
        return False
    return True


def to_whatsapp_number(raw: str) -> str:
    """wa.me expects digits only, no plus sign."""
    return normalize_phone(raw).lstrip("+")
