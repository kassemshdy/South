"""Turning a pydantic error into a sentence the reader can actually read.

Pydantic writes its own messages, in English, and nothing about the request
locale reaches it: ``String should have at least 2 characters`` came back
verbatim under ``Accept-Language: ar``. So every 422 handed an Arabic reader
an English sentence under a correctly-translated envelope -- the one place in
the app where a user-facing string was not in a catalog.

The mapping is by pydantic's ``type`` discriminator, which is stable across
2.x and is the same identifier its own documentation indexes errors under.
Anything unmapped falls back to a generic sentence and is logged, following
the rule the rest of ``i18n`` follows: a translation gap should be visible
and ugly, never a blank screen or -- worse here -- a silent relapse into
English.

**Only whitelisted context values are interpolated.** Pydantic puts an
English explanation in ``ctx['error']`` for parse failures (the UUID one is a
sentence about ``urn:uuid:`` prefixes), so a mapping that passed ``**ctx``
through would leak exactly the English this module exists to remove. The one
exception is ``value_error``, where ``ctx['error']`` is a ``ValueError`` this
codebase raised itself, already rendered through ``translate()`` in the
reader's locale.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from app.core.i18n import translate

logger = logging.getLogger(__name__)

FALLBACK_KEY = "error.field_invalid"

# pydantic error type -> the ctx keys that type supplies and the catalog
# template is allowed to interpolate. An empty tuple means the sentence takes
# no parameters.
_PARAMS: dict[str, tuple[str, ...]] = {
    # Presence
    "missing": (),
    # Length, on strings and on lists alike
    "string_too_short": ("min_length",),
    "string_too_long": ("max_length",),
    "too_short": ("min_length",),
    "too_long": ("max_length",),
    # Range
    "greater_than": ("gt",),
    "greater_than_equal": ("ge",),
    "less_than": ("lt",),
    "less_than_equal": ("le",),
    # Shape -- "this is not a number at all", rather than "out of range"
    "string_type": (),
    "int_type": (),
    "int_parsing": (),
    "float_type": (),
    "float_parsing": (),
    "decimal_type": (),
    "decimal_parsing": (),
    "bool_type": (),
    "bool_parsing": (),
    "uuid_type": (),
    "uuid_parsing": (),
    "date_type": (),
    "date_parsing": (),
    "date_from_datetime_parsing": (),
    "datetime_type": (),
    "datetime_parsing": (),
    "datetime_from_date_parsing": (),
    "list_type": (),
    "dict_type": (),
    "json_invalid": (),
    "enum": (),
    "literal_error": (),
}


def _field_name(loc: tuple[Any, ...]) -> str:
    """The dotted path of the offending field, minus the ``body``/``query``
    prefix pydantic prepends -- the frontend matches this against its own
    input names to highlight the right box."""
    return ".".join(str(part) for part in loc[1:]) or "body"


def describe(error: dict[str, Any]) -> str:
    """Render one pydantic error in the request's locale."""
    kind = str(error.get("type", ""))
    ctx: dict[str, Any] = error.get("ctx") or {}

    if kind == "value_error":
        # Raised by this codebase's own ``@field_validator``s, which build
        # their message with ``translate()`` -- so it is already in the
        # reader's locale, and pydantic's "Value error, " prefix is the only
        # English on it. ``ctx['error']`` is that exception without the
        # prefix; ``msg`` is the fallback if a pydantic version stops
        # supplying it.
        raised = ctx.get("error")
        if raised is not None:
            return str(raised)
        return str(error.get("msg", "")).removeprefix("Value error, ") or translate(
            FALLBACK_KEY
        )

    allowed = _PARAMS.get(kind)
    if allowed is None:
        # Not a relapse into English: a generic sentence, and a log line so
        # the gap can be closed rather than discovered by a user.
        logger.warning("Unmapped validation error type", extra={"error_type": kind})
        return translate(FALLBACK_KEY)

    params = {name: ctx[name] for name in allowed if name in ctx}
    return translate(f"validation.{kind}", **params)


def field_errors(errors: Sequence[Any]) -> list[dict[str, str]]:
    """The ``details.fields`` payload: one translated sentence per field.

    ``Sequence[Any]`` rather than the obvious ``list[dict[str, Any]]``
    because that is what ``RequestValidationError.errors()`` is annotated as;
    each element is in fact one of pydantic's error dicts.
    """
    return [
        {"field": _field_name(tuple(error.get("loc", ()))), "message": describe(error)}
        for error in errors
    ]
