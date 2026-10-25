"""Reading uploads with a bound.

The Content-Disposition half of this module moved to ``app.core.downloads``,
which develop-claude added independently for the same bug.
"""

from __future__ import annotations

from typing import BinaryIO

#: Read granularity, so the bound below is reached in steps rather than by one
#: read that could itself be enormous.
_CHUNK_BYTES = 64 * 1024


def read_at_most(fileobj: BinaryIO, limit: int) -> bytes:
    """Read an upload, but never more than ``limit + 1`` bytes of it.

    ``file.read()`` materialised the whole part in memory before any size check
    ran, so the check guarded nothing: an oversized body was already fully in
    RAM by the time it was measured. This stops one byte past ``limit``, which
    bounds memory however large the request -- and is still enough for every
    caller's existing ``len(data) > limit`` check to fire and refuse the file
    with the message it always has. Deliberately not a new check of its own:
    the routes and services already decide what "too large" says.
    """
    budget = limit + 1
    chunks: list[bytes] = []
    while budget > 0:
        chunk = fileobj.read(min(_CHUNK_BYTES, budget))
        if not chunk:
            break
        chunks.append(chunk)
        budget -= len(chunk)
    return b"".join(chunks)

