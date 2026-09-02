"""The OTP delivery seam.

Authentication logic depends on this protocol only, so swapping the mock
provider for Twilio, a WhatsApp Business sender, or a Lebanese SMS aggregator is
a configuration change plus one new file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class OtpSendResult:
    """Outcome of a delivery attempt.

    ``debug_code`` is populated only by development providers and is surfaced to
    the client only when the application runs in development mode.
    """

    delivered: bool
    provider: str
    debug_code: str | None = None
    provider_message_id: str | None = None


@runtime_checkable
class OtpProvider(Protocol):
    name: str

    def send(self, phone_number: str, code: str) -> OtpSendResult:
        """Deliver ``code`` to ``phone_number`` (already E.164 normalized)."""
        ...

    def fixed_code(self) -> str | None:
        """Return a deterministic code when the provider mandates one.

        Real providers return None; only development adapters may pin a code.
        """
        ...
