"""Declared status transitions.

A status column whose rules live only in ``if`` statements spread across
services is a state machine nobody can read in one place. This helper
holds the rule as data -- target status -> the statuses it may be entered
from -- so the service, its tests, the API error and an agent reading the
code all see the same table. Moderation of businesses keeps its own
action-based table (``app.services.moderation.TRANSITIONS``); this is for
the simpler "may X move to Y" machines.

Only targets listed in ``guarded`` are checked; every other move stays
free, so a table can start with the one rule that matters and grow.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping
from typing import Generic, TypeVar

from app.core.errors import ConflictError

StatusT = TypeVar("StatusT", bound=enum.Enum)


class Transitions(Generic[StatusT]):
    def __init__(
        self,
        guarded: Mapping[StatusT, frozenset[StatusT]],
        *,
        message_key: str,
        code: str = "invalid_status_transition",
    ) -> None:
        self.guarded = dict(guarded)
        self._message_key = message_key
        self._code = code

    def allows(self, current: StatusT, target: StatusT) -> bool:
        """Staying put (a reorder, a repeat click) is always allowed."""
        if current is target:
            return True
        sources = self.guarded.get(target)
        return sources is None or current in sources

    def check(self, current: StatusT, target: StatusT) -> None:
        if not self.allows(current, target):
            raise ConflictError(
                self._message_key,
                code=self._code,
                details={
                    "current_status": current.value,
                    "target_status": target.value,
                    "allowed_from": sorted(s.value for s in self.guarded[target]),
                },
            )
