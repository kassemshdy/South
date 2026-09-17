"""Temporary passwords issued by an administrator.

Readable out loud and typed on a phone keyboard, because that is what actually
happens to one: an administrator reads it into a WhatsApp message and a shop
owner types it into a login form, often on a cracked screen in bright sun.

So the alphabet drops the characters that get misread — O/0, I/l/1 — and the
shape is grouped rather than one run of noise. What is lost in entropy per
character is bought back by length, and the password is single-use anyway:
`must_change_password` means it opens the account once and is then replaced.
"""

from __future__ import annotations

import secrets

# No O, 0, I, l or 1: every pair of those is the classic misread, and a person
# retyping from a chat message has no way to tell which one was meant.
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
_GROUP = 4
_GROUPS = 3


def generate_temporary_password() -> str:
    """A grouped, unambiguous password, e.g. ``k7Rm-2pQw-Xh4n``."""
    groups = [
        "".join(secrets.choice(_ALPHABET) for _ in range(_GROUP)) for _ in range(_GROUPS)
    ]
    return "-".join(groups)
