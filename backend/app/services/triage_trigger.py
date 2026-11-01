"""Start the scheduled triage routine as soon as a person hands it work.

The routine runs every few hours on its own. When a person moves a ticket to
``TODO`` (fix this now) or ``APPROVED`` (release this now), this module calls
the routine's API trigger so the work starts within a minute instead of
waiting for the next scheduled run (the owners' request, 1 Nov 2026).

A run is billed to the owners' Claude subscription, not an API key: the
trigger's URL and bearer token are created in the routine's settings on
claude.ai and set here as ``CLAUDE_TRIAGE_FIRE_URL`` / ``CLAUDE_TRIAGE_TOKEN``.
Inert without both, like every other optional integration.

Only a ticket's id and its new column are sent. Ticket text is written by
other people, and it reaches the routine through the board, where the skill
treats it as a description of a problem -- never through this message.

Each call starts a new session and the API has no idempotency key, so calls
inside ``DEBOUNCE_SECONDS`` of the last one are skipped: one run takes one
ticket and starts with any approved release, so dragging several cards in a
row needs one run, not several. Anything skipped is picked up by the next
run, scheduled or fired. The call is made off the request thread, so a slow
or failing trigger never delays or fails a move on the board.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

import httpx

from app.core.config import Settings, get_settings
from app.models.enums import FeedbackStatus

logger = logging.getLogger(__name__)

#: The columns a person moves a ticket into to hand the routine work.
FIRING_STATUSES = frozenset({FeedbackStatus.TODO, FeedbackStatus.APPROVED})
#: Required by the routine fire endpoint.
API_VERSION = "2026-10-21"
DEBOUNCE_SECONDS = 300.0

_lock = threading.Lock()
_last_fired: float | None = None


def reset() -> None:
    """Forget the last call -- for tests."""
    global _last_fired
    with _lock:
        _last_fired = None


def _claim(now: float) -> bool:
    global _last_fired
    with _lock:
        if _last_fired is not None and now - _last_fired < DEBOUNCE_SECONDS:
            return False
        _last_fired = now
        return True


def request_body(ticket_id: str, status: FeedbackStatus) -> dict[str, str]:
    return {
        "text": (
            f"A person moved support ticket {ticket_id} to {status.value}. "
            "Run one pass of the triage-loop skill now."
        )
    }


def _post(url: str, token: str, body: dict[str, str], client: httpx.Client | None) -> None:
    owned = client is None
    http = client or httpx.Client(timeout=30)
    try:
        response = http.post(
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-version": API_VERSION,
            },
        )
        if response.status_code >= 400:
            # The body may echo the request; the status says enough.
            logger.warning("Triage routine trigger refused", extra={"status": response.status_code})
        else:
            logger.info("Triage routine fired")
    except httpx.HTTPError as exc:
        logger.warning("Triage routine trigger failed", extra={"error": type(exc).__name__})
    finally:
        if owned:
            http.close()


def fire(
    ticket_id: str,
    status: FeedbackStatus,
    *,
    settings: Settings | None = None,
    client: httpx.Client | None = None,
    run: Callable[[Callable[[], None]], None] | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    """Ask the routine to start; True when a call was made (or queued).

    ``client`` and ``run`` exist for tests: by default the call goes out on
    a daemon thread with its own client.
    """
    if status not in FIRING_STATUSES:
        return False
    settings = settings or get_settings()
    url, token = settings.claude_triage_fire_url, settings.claude_triage_token
    if not (url and token):
        return False
    if not _claim(clock()):
        return False
    body = request_body(ticket_id, status)

    def call() -> None:
        _post(url, token, body, client)

    if run is not None:
        run(call)
    else:
        threading.Thread(target=call, name="triage-trigger", daemon=True).start()
    return True
