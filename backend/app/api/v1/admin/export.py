"""The administrator's off-platform copy of the directory.

See ``app.services.data_export`` for what the workbook holds and why. The
route only adds what a download needs: the filename, and headers that keep a
file full of identity data out of every cache between here and the browser.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Response

from app.core.dependencies import AdminUser, DbSession
from app.services.data_export import build_workbook, log_export

router = APIRouter(prefix="/admin", tags=["admin-export"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/export")
def export_data(db: DbSession, admin: AdminUser) -> Response:
    content = build_workbook(db)
    log_export(admin, len(content))
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    return Response(
        content=content,
        media_type=XLSX,
        headers={
            "Content-Disposition": f'attachment; filename="janoubona-export-{stamp}.xlsx"',
            "Cache-Control": "no-store",
        },
    )
