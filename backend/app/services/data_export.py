"""A workbook of the directory, for an administrator to keep off the platform.

The database is already copied into the bucket at every boot and once a day
(``app.services.db_backup``), and that dump is what ``docs/RESTORE.md``
restores from. This is the other copy: one a person can open, read and keep
on their own machine, so that losing Railway -- the database and the bucket
together -- does not lose the people who applied and what they listed.

Each sheet is one table, every column of it, with the ids that link them
(``owner_id``, ``business_id``, ``category_id``...), so the rows can be put
back by hand or by a script. Columns come from the model rather than a list
written here, so a column added later is exported without anyone remembering
to add it.

What it deliberately leaves out:

- **Credentials.** ``password_hash`` and ``token_version`` are worth nothing
  to a restore -- a restored account is issued a new password -- and a hash
  in a spreadsheet is a hash someone can attack offline.
- **Files.** ID scans, CVs and photographs live in the bucket, not in these
  rows; a storage key is kept, the bytes are not.

It does hold every account holder's identity, which is the point of it and
also why it is an administrator-only download that is never cached.
"""

from __future__ import annotations

import enum
import json
import logging
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.business import Business, BusinessItem
from app.models.talent import TalentProfile, TalentSkill
from app.models.taxonomy import Category, Location
from app.models.user import User

logger = logging.getLogger(__name__)

#: Sheet name and table, in the order a restore would put them back: the
#: reference tables the others point at last, so the four the owners asked
#: for open first.
SHEETS: tuple[tuple[str, type[Base]], ...] = (
    ("people", User),
    ("talents", TalentProfile),
    ("businesses", Business),
    ("items", BusinessItem),
    ("categories", Category),
    ("locations", Location),
    ("talent_skills", TalentSkill),
)

#: Never exported, whatever table they appear on. See the module docstring.
EXCLUDED_COLUMNS = frozenset({"password_hash", "token_version"})


def build_workbook(db: Session) -> bytes:
    """The whole export as the bytes of an ``.xlsx`` file."""
    workbook = Workbook()
    # A new workbook starts with an empty sheet; the first table takes it over.
    first = True
    for title, model in SHEETS:
        sheet = workbook.active if first else workbook.create_sheet()
        first = False
        sheet.title = title
        _fill(sheet, db, model)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _fill(sheet: Worksheet, db: Session, model: type[Base]) -> None:
    columns = [
        column
        for column in inspect(model).columns
        if column.key not in EXCLUDED_COLUMNS
    ]
    sheet.append([column.key for column in columns])
    sheet.freeze_panes = "A2"

    rows = db.execute(select(*columns).order_by(*inspect(model).primary_key)).all()
    for row in rows:
        sheet.append([_cell(value) for value in row])
        _keep_text_as_text(sheet)


def _cell(value: Any) -> Any:
    """A value openpyxl can store and Excel will show as it was entered."""
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, datetime):
        # Excel has no time zones and openpyxl refuses an aware datetime;
        # every timestamp here is UTC, which the column name does not say,
        # so it is converted rather than silently stripped.
        return value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, date):
        return value
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False)
    # Text typed by applicants. Control characters other than tab and
    # newline are not allowed in the file format and would abort the whole
    # export, so they are dropped.
    return ILLEGAL_CHARACTERS_RE.sub("", str(value))


def _keep_text_as_text(sheet: Worksheet) -> None:
    """Store the row just appended so no text in it can run as a formula.

    openpyxl writes any string starting with ``=`` as a formula, and every
    text cell here was typed by a member of the public. A listing named
    ``=HYPERLINK(...)`` must open as that text, not as a live link on the
    administrator's machine.
    """
    for cell in sheet[sheet.max_row]:
        if isinstance(cell.value, str) and cell.data_type == "f":
            cell.data_type = "s"


def log_export(admin: User, size: int) -> None:
    logger.info(
        "Data exported",
        extra={"admin_id": str(admin.id), "size_bytes": size},
    )
