"""Slug generation.

Slugs keep their original script: "مناقيش الضيعة" becomes "مناقيش-الضيعة" rather
than the vowel-less transliteration "mnqysh-ldy", which is meaningless to an
Arabic reader and worthless for Arabic search. Latin names are unaffected —
"Abu Ali Bakery" still yields "abu-ali-bakery". Browsers and crawlers handle
percent-encoded UTF-8 paths and display them decoded.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable

from slugify import slugify

MAX_SLUG_LENGTH = 120


def slugify_name(name: str) -> str:
    base = slugify(
        name,
        max_length=MAX_SLUG_LENGTH,
        word_boundary=True,
        lowercase=True,
        allow_unicode=True,
    )
    if not base:
        base = f"business-{secrets.token_hex(3)}"
    return base


def unique_slug(name: str, exists: Callable[[str], bool]) -> str:
    """Return a slug that ``exists`` reports as free.

    Appends -2, -3, ... and finally a random suffix, so concurrent creates
    cannot spin forever on a contended name.
    """
    base = slugify_name(name)
    if not exists(base):
        return base

    for suffix in range(2, 51):
        candidate = f"{base}-{suffix}"
        if not exists(candidate):
            return candidate

    return f"{base}-{secrets.token_hex(4)}"
