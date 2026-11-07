"""Telegram notices for what staff do: a follow-up note on a shop with no
products, a listing approved or rejected (the owners' requests, 7 Nov 2026).

Each names the staff member who did it. Sent after the commit, through the
archive's own queue, and nothing at all when Telegram is not configured.
"""

from __future__ import annotations

from app.models.user import User
from app.services import telegram_archive


def staff_name(admin: User) -> str | None:
    """The name the team knows a staff member by."""
    return admin.display_name or admin.full_name or admin.email


def moderated(
    *,
    approved: bool,
    listing: str,
    name: str,
    admin: User,
    reason: str | None,
    path: str,
) -> None:
    """A listing approved or rejected: ``listing`` is ``shop`` or ``service``."""
    verdict = "approved" if approved else "rejected"
    telegram_archive.notify(
        telegram_archive.Notice(
            title_key=f"telegram.kind.{listing}_{verdict}",
            rows=[
                (listing, name),
                ("reason", None if approved else reason),
                ("staff", staff_name(admin)),
            ],
            path=path,
        )
    )
