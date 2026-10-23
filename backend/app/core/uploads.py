"""Reading uploads and serving stored files over HTTP, safely.

Two small helpers that every upload and download route used to reimplement,
each with the same gap.
"""

from __future__ import annotations

import re
from typing import BinaryIO
from urllib.parse import quote

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


# Printable ASCII with the two characters that would end or escape a quoted
# string removed. Everything else becomes an underscore in the fallback.
_UNSAFE_ASCII = re.compile(r'[^\x20-\x7e]|["\\]')


def content_disposition(filename: str, *, inline: bool = False) -> str:
    """A ``Content-Disposition`` value that cannot be broken by its filename.

    The filename is applicant-supplied. Interpolated raw into
    ``filename="..."`` a double quote ended the parameter early and left the
    rest as header syntax. RFC 6266 answers both halves of the problem: a
    plain-ASCII ``filename`` with anything unsafe replaced, for old clients,
    and ``filename*`` carrying the real name percent-encoded as UTF-8 -- which
    is also what makes an Arabic filename survive the download at all.
    """
    disposition = "inline" if inline else "attachment"
    fallback = _UNSAFE_ASCII.sub("_", filename).strip() or "download"
    encoded = quote(filename, safe="")
    return f"{disposition}; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"
