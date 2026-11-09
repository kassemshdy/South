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
import logging
import tempfile
import zipfile
from collections.abc import Iterable, Iterator, Sequence
from typing import Any, Literal

from fastapi import APIRouter
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, class_mapper, joinedload, selectinload

from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.models.business import Business, BusinessItem
from app.models.enums import VerificationDocumentKind
from app.models.order import Order
from app.models.partner import PartnerRequest
from app.models.talent import TalentProfile
from app.models.user import User
from app.models.verification import OwnerVerificationDocument
from app.services.verification import VerificationDocumentService
from app.storage.factory import get_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/export", tags=["admin-export"])

Dataset = Literal["businesses", "products", "users", "talent", "orders", "partners"]

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


def dataset_csv(db: Session, dataset: Dataset) -> bytes:
    """One dataset as a UTF-8 CSV with a byte-order mark, as Excel needs.
    Shared by the download below and the Telegram backup."""
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
    elif dataset == "partners":
        # Open and solved alike: a solved request is archived, not gone, and
        # the owners asked for every one in a sheet (29 Oct 2026). ``solved_at``
        # says which is which.
        model = PartnerRequest
        objects = (
            db.execute(select(PartnerRequest).order_by(PartnerRequest.created_at)).scalars().all()
        )
        extra = {}
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
    return codecs.BOM_UTF8 + buffer.getvalue().encode("utf-8")


#: Every dataset, in the order the Telegram backup sends them.
DATASETS: tuple[Dataset, ...] = ("businesses", "products", "users", "talent", "orders", "partners")


@router.get("/id-documents.zip")
def export_id_documents(db: DbSession, admin: AdminUser, settings: AppSettings) -> Response:
    """Every account's ID scans, front and back, in one zip (the owners'
    request, 9 Nov 2026). The manager's alone (``RESTRICTED_READS``): it is
    every identity paper on the site at once. Written to a temporary file
    rather than memory, since hundreds of photographs add up; stored, not
    compressed, as photographs do not shrink. Each download is logged with
    the administrator's id."""
    documents = (
        db.execute(
            select(OwnerVerificationDocument)
            .options(joinedload(OwnerVerificationDocument.user))
            .where(
                OwnerVerificationDocument.kind.in_(
                    (VerificationDocumentKind.IDENTITY, VerificationDocumentKind.IDENTITY_BACK)
                )
            )
            .order_by(OwnerVerificationDocument.created_at)
        )
        .unique()
        .scalars()
        .all()
    )
    service = VerificationDocumentService(get_storage(), settings)
    spool = tempfile.SpooledTemporaryFile(max_size=32 * 1024 * 1024)  # noqa: SIM115
    missing = 0
    with zipfile.ZipFile(spool, "w", compression=zipfile.ZIP_STORED) as archive:
        for document in documents:
            try:
                data = service.read_bytes(document)
            except Exception:  # a file gone from storage must not sink the rest
                missing += 1
                logger.warning("ID scan missing from storage", extra={"document": str(document.id)})
                continue
            archive.writestr(_id_file_name(document), data)
    logger.info(
        "ID scans exported",
        extra={"admin_id": str(admin.id), "files": len(documents) - missing, "missing": missing},
    )
    spool.seek(0)
    stamp = dt.date.today().isoformat()

    def chunks() -> Iterator[bytes]:
        try:
            while chunk := spool.read(1024 * 1024):
                yield chunk
        finally:
            spool.close()

    return StreamingResponse(
        chunks(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="id-documents-{stamp}.zip"'},
    )


_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}


def _id_file_name(document: OwnerVerificationDocument) -> str:
    """``<account number>_<front|back>.<ext>``, the account id when there is
    no number, so each file says whose it is without opening it."""
    user = document.user
    who = (user.phone_number or "").lstrip("+") if user is not None else ""
    side = "front" if document.kind == VerificationDocumentKind.IDENTITY else "back"
    ext = _EXTENSIONS.get(document.content_type, "")
    return f"{who or document.user_id}_{side}{ext}"


@router.get("/{dataset}.csv")
def export_dataset(dataset: Dataset, db: DbSession, admin: AdminUser) -> Response:
    stamp = dt.date.today().isoformat()
    return Response(
        content=dataset_csv(db, dataset),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{dataset}-{stamp}.csv"'},
    )
