"""Text messages through bestsmsbulk.com (the owners' request, 9 Nov 2026).

Staff send one SMS at a time, to a shop owner's account number, from the
admin screens -- never a bulk send from the code. Inert without
``BESTSMS_API_KEY``, ``BESTSMS_API_SECRET`` and ``BESTSMS_SENDER_ID``: the
admin screens then show no SMS button and nothing leaves the server.

Messages go through the provider's JSON send API. Its plain-text one
(``sendSmsAPI.php``) refused the account's approved sender ID with
"senderid is not authorized" while the JSON one, with the same key and
sender, delivered (checked 9 Nov 2026). The JSON API answers
``{"status": 201, "data": [{"confirmationid": ..., "numberofsmspermsg": n}]}``
on success and ``{"status": 300, "message": "..."}`` on failure; the
message is passed to staff as it is. The key and secret travel in the POST
body, never in a URL, so they cannot reach an access log.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import ValidationError
from app.core.phone import to_whatsapp_number

logger = logging.getLogger(__name__)

SEND_URL = "https://www.bestsmsbulk.com/bestsmsbulkapi/sendSmsAPIJson.php"
BALANCE_URL = "https://www.bestsmsbulk.com/bestsmsbulkapi/getbalance.php"


@dataclass
class SmsSent:
    confirmation_id: str
    parts: int


class SmsError(Exception):
    """The provider refused the message; ``str()`` is its own reason."""


class SmsService:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.Client(timeout=20)

    @property
    def enabled(self) -> bool:
        return self._settings.sms_enabled

    def _credentials(self) -> dict[str, str]:
        if not self.enabled:
            raise SmsError("SMS is not configured")
        return {
            "api_key": self._settings.bestsms_api_key or "",
            "api_secret": self._settings.bestsms_api_secret or "",
        }

    def send(self, phone: str, message: str) -> SmsSent:
        """Send ``message`` to one Lebanese number, in the provider's
        96170XXXXXX form. Raises SmsError with the provider's reason."""
        try:
            destination = to_whatsapp_number(phone)
        except ValidationError as error:
            raise SmsError("invalid phone number") from error
        response = self._client.post(
            SEND_URL,
            json=[
                {
                    **self._credentials(),
                    "senderid": self._settings.bestsms_sender_id or "",
                    "destination": destination,
                    "message": message,
                }
            ],
        )
        try:
            body: Any = response.json()
        except ValueError:
            body = None
        if not isinstance(body, dict):
            reason = response.text.strip().splitlines()[0] if response.text.strip() else ""
            logger.warning("SMS refused", extra={"status": response.status_code, "reason": reason})
            raise SmsError(reason or f"HTTP {response.status_code}")
        rows = body.get("data") if isinstance(body.get("data"), list) else []
        row = rows[0] if rows and isinstance(rows[0], dict) else {}
        if body.get("status") == 201 and row.get("confirmationid") is not None:
            parts_raw = row.get("numberofsmspermsg")
            parts = int(str(parts_raw)) if str(parts_raw).isdigit() else 1
            confirmation = str(row["confirmationid"])
            logger.info("SMS sent", extra={"confirmation_id": confirmation, "parts": parts})
            return SmsSent(confirmation_id=confirmation, parts=parts)
        reason = str(row.get("message") or body.get("message") or "")
        logger.warning("SMS refused", extra={"status": response.status_code, "reason": reason})
        raise SmsError(reason or f"HTTP {response.status_code}")

    def balance(self) -> float | None:
        """The account's credit, or None when the provider will not say."""
        response = self._client.post(BALANCE_URL, data=self._credentials())
        try:
            return float(response.text.strip())
        except ValueError:
            logger.warning("SMS balance unreadable", extra={"status": response.status_code})
            return None
