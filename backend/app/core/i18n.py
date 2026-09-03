"""Message catalogs and locale resolution.

No user-facing string is written in Python source. Everything lives in
``app/locales/<locale>.json`` so that adding a language is a translation task,
not a code change.

The active locale is held in a context variable set once per request by
middleware. Starlette copies the context into the threadpool it runs sync
endpoints in, so services deep in the call stack can translate without being
handed a locale argument.
"""

from __future__ import annotations

import contextvars
import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

logger = logging.getLogger(__name__)

DEFAULT_LOCALE: Final = "ar"
SUPPORTED_LOCALES: Final = ("ar", "en")

_LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"

current_locale: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_locale", default=DEFAULT_LOCALE
)


@lru_cache(maxsize=len(SUPPORTED_LOCALES))
def _catalog(locale: str) -> dict[str, str]:
    path = _LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        logger.error("Missing locale catalog", extra={"locale": locale})
        return {}
    data: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
    return data


def available_locales() -> tuple[str, ...]:
    return SUPPORTED_LOCALES


def set_locale(locale: str) -> contextvars.Token[str]:
    return current_locale.set(normalize_locale(locale))


def normalize_locale(locale: str | None) -> str:
    if not locale:
        return DEFAULT_LOCALE
    base = locale.split("-")[0].strip().lower()
    return base if base in SUPPORTED_LOCALES else DEFAULT_LOCALE


def resolve_locale(accept_language: str | None) -> str:
    """Pick a locale from an Accept-Language header.

    Ordered by q-value, falling back to the default when nothing matches, so an
    Arabic-speaking visitor with an English browser still gets a usable site.
    """
    if not accept_language:
        return DEFAULT_LOCALE

    candidates: list[tuple[float, str]] = []
    for part in accept_language.split(","):
        piece, _, params = part.strip().partition(";")
        quality = 1.0
        if params.startswith("q="):
            try:
                quality = float(params[2:])
            except ValueError:
                quality = 0.0
        language = piece.split("-")[0].strip().lower()
        if language in SUPPORTED_LOCALES:
            candidates.append((quality, language))

    if not candidates:
        return DEFAULT_LOCALE
    return max(candidates, key=lambda item: item[0])[1]


@dataclass(frozen=True)
class LazyText:
    """A message that must be rendered in the *reader's* locale, not the writer's.

    Errors are raised deep in the service layer but rendered later, once the
    response locale is known. Passing a LazyText as a parameter defers its
    translation to that point, so an English reader does not receive an English
    sentence with an Arabic word embedded in it.
    """

    key: str
    params: dict[str, Any] = field(default_factory=dict)

    def resolve(self, locale: str | None = None) -> str:
        return translate(self.key, locale, **self.params)


@dataclass(frozen=True)
class LazyJoin:
    """Several deferred messages joined with a translated separator."""

    keys: tuple[str, ...]
    separator_key: str = "business.list_separator"

    def resolve(self, locale: str | None = None) -> str:
        separator = translate(self.separator_key, locale)
        return separator.join(translate(key, locale) for key in self.keys)


def _resolve_params(params: dict[str, Any], locale: str | None) -> dict[str, Any]:
    return {
        name: value.resolve(locale) if hasattr(value, "resolve") else value
        for name, value in params.items()
    }


def translate(key: str, /, locale: str | None = None, **params: Any) -> str:
    """Render ``key`` in ``locale`` (or the request's locale).

    A missing key falls back to the default locale and finally to the key
    itself, logging as it goes: a translation gap should be visible and ugly,
    never a blank screen or a 500.
    """
    active = normalize_locale(locale) if locale else current_locale.get()

    template = _catalog(active).get(key)
    if template is None and active != DEFAULT_LOCALE:
        template = _catalog(DEFAULT_LOCALE).get(key)
        if template is not None:
            logger.warning(
                "Missing translation", extra={"message_key": key, "locale": active}
            )
    if template is None:
        logger.error("Unknown message key", extra={"message_key": key, "locale": active})
        return key

    if not params:
        return template
    try:
        return template.format(**_resolve_params(params, active))
    except (KeyError, IndexError):
        logger.error(
            "Message parameters do not match the template",
            extra={"message_key": key, "locale": active, "params": sorted(params)},
        )
        return template


def translate_all(keys: list[str], locale: str | None = None) -> list[str]:
    return [translate(key, locale) for key in keys]
