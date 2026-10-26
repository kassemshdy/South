"""Spreadsheet exports for the administrators.

One CSV per dataset, every row and every column a person entered, so the
owners can open their data in Excel without a technical person. Written with
a UTF-8 byte-order mark: without it Excel reads the file as Latin-1 and the
Arabic comes out as mojibake.

Administrator-only, and it carries what the review screens carry -- owners'
identity fields and customers' phone numbers -- so a downloaded file is as
sensitive as the admin area itself. Never exported: password hashes, session
counters and storage keys (``_SKIPPED``).
"""

from __future__ import annotations

import codecs
import csv
import datetime as dt
import enum
import io
from collections.abc import Iterable, Sequence
from typing import Any, Literal

from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import class_mapper, joinedload, selectinload

from app.core.dependencies import AdminUser, DbSession
from app.models.business import Business, BusinessItem
from app.models.order import Order
from app.models.talent import TalentProfile
from app.models.user import User

router = APIRouter(prefix="/admin/export", tags=["admin-export"])

Dataset = Literal["businesses", "products", "users", "talent", "orders"]

_SKIPPED = frozenset({"password_hash", "token_version", "search_vector"})


#: A cell starting with one of these is a formula to Excel and Sheets. Every
#: text column here was typed by someone outside -- a listing's name, an
#: applicant's, a customer's note -- so ``=HYPERLINK(...)`` in a shop name
#: would run on the administrator's machine when the export is opened.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, enum.Enum):
        return str(value.value)
    if isinstance(value, dt.date):  # datetime is a date too
        return value.isoformat()
    if isinstance(value, str):
        # A leading apostrophe makes the spreadsheet show the text as typed.
        # Only text: a number is never a formula, and "-3.5" must stay a number.
        return f"'{value}" if value.startswith(_FORMULA_PREFIXES) else value
    return str(value)


def _columns(model: type) -> list[str]:
    return [
        attr.key
        for attr in class_mapper(model).column_attrs
        if attr.key not in _SKIPPED and not attr.key.endswith("storage_key")
    ]


def _rows(objects: Iterable[Any], columns: Sequence[str], extra: dict[str, Any]) -> list[list[str]]:
    return [
        [_cell(getattr(obj, name)) for name in columns]
        + [_cell(compute(obj)) for compute in extra.values()]
        for obj in objects
    ]


def _owner(obj: Any) -> str:
    owner = getattr(obj, "owner", None)
    return (owner.phone_number or owner.email or "") if owner is not None else ""


@router.get("/{dataset}.csv")
def export_dataset(dataset: Dataset, db: DbSession, admin: AdminUser) -> Response:
    model: type
    extra: dict[str, Any]
    if dataset == "businesses":
        model = Business
        objects: Sequence[Any] = (
            db.execute(select(Business).options(joinedload(Business.owner)).order_by(Business.created_at))
            .unique()
            .scalars()
            .all()
        )
        extra = {"owner_phone": _owner}
    elif dataset == "products":
        model = BusinessItem
        objects = (
            db.execute(
                select(BusinessItem)
                .options(joinedload(BusinessItem.business))
                .order_by(BusinessItem.created_at)
            )
            .unique()
            .scalars()
            .all()
        )
        extra = {
            "business_name": lambda item: item.business.name,
            "business_slug": lambda item: item.business.slug,
        }
    elif dataset == "users":
        model = User
        objects = db.execute(select(User).order_by(User.created_at)).scalars().all()
        extra = {}
    elif dataset == "talent":
        model = TalentProfile
        objects = (
            db.execute(
                select(TalentProfile)
                .options(joinedload(TalentProfile.owner))
                .order_by(TalentProfile.created_at)
            )
            .unique()
            .scalars()
            .all()
        )
        extra = {"owner_phone": _owner}
    else:
        model = Order
        objects = (
            db.execute(
                select(Order)
                .options(joinedload(Order.business), selectinload(Order.lines))
                .order_by(Order.created_at)
            )
            .unique()
            .scalars()
            .all()
        )
        extra = {
            "business_name": lambda order: order.business.name,
            "items": lambda order: "; ".join(
                f"{line.title} x{line.quantity}" for line in order.lines
            ),
        }

    columns = _columns(model)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([*columns, *extra])
    writer.writerows(_rows(objects, columns, extra))

    stamp = dt.date.today().isoformat()
    return Response(
        content=codecs.BOM_UTF8 + buffer.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{dataset}-{stamp}.csv"'},
    )
