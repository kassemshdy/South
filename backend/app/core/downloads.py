"""The Content-Disposition header for a file sent back to a browser.

HTTP headers are Latin-1, and a file's original name is whatever the person
who uploaded it called it -- often Arabic. Putting that name straight into
``filename="..."`` raised a UnicodeEncodeError, so an administrator opening
an applicant's ID scan got a 500 instead of the file. RFC 6266 sends both: an
ASCII ``filename`` for old clients and the real name, percent-encoded, as
``filename*``, which every current browser prefers.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Literal
from urllib.parse import quote

_UNSAFE = re.compile(r'[^A-Za-z0-9._-]+')


def content_disposition(
    filename: str, *, disposition: Literal["attachment", "inline"] = "attachment"
) -> str:
    name = PurePosixPath(filename.replace("\\", "/")).name or "file"
    path = PurePosixPath(name)
    stem = _UNSAFE.sub("_", path.stem).strip("_.-") or "file"
    fallback = f"{stem}{_UNSAFE.sub('', path.suffix)}"
    return f"{disposition}; filename=\"{fallback}\"; filename*=UTF-8''{quote(name, safe='')}"
