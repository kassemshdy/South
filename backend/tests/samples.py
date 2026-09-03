"""Arabic sample text used by the tests.

The suite needs real Arabic to prove that search normalization, RTL slugs and
SEO tags work. Keeping those samples in a JSON fixture rather than inline
literals means the no-Arabic-in-code guard stays meaningful, and the strings can
be inspected in one place.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "arabic_samples.json"


@lru_cache(maxsize=1)
def _samples() -> dict[str, str]:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def ar(key: str) -> str:
    """Return the Arabic sample registered under ``key``."""
    try:
        return _samples()[key]
    except KeyError:  # pragma: no cover - a typo in a test, surfaced loudly
        raise KeyError(
            f"Unknown Arabic sample '{key}'. Add it to {_FIXTURE.name}."
        ) from None
