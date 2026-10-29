"""Administrators' spreadsheet export.

What matters: it is administrator-only, it opens correctly in Excel (UTF-8
with a byte-order mark, so Arabic survives), and it never carries a password
hash or a storage key.
"""

from __future__ import annotations

import csv
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from tests.conftest import admin_headers, make_owner, sign_in

DATASETS = ["businesses", "products", "users", "talent", "orders", "partners"]


def _read(body: bytes) -> list[dict[str, str]]:
    assert body.startswith(b"\xef\xbb\xbf"), "Excel needs the BOM to read UTF-8"
    return list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))


@pytest.mark.parametrize("dataset", DATASETS)
def test_each_dataset_downloads_as_csv(client: TestClient, admin: User, dataset: str) -> None:
    response = client.get(f"/api/admin/export/{dataset}.csv", headers=admin_headers(client))

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert f'filename="{dataset}-' in response.headers["content-disposition"]
    _read(response.content)


def test_users_export_carries_accounts_but_never_a_password_hash(
    client: TestClient, admin: User
) -> None:
    make_owner("03990301")

    rows = _read(
        client.get("/api/admin/export/users.csv", headers=admin_headers(client)).content
    )

    assert any(row["phone_number"].endswith("3990301") for row in rows)
    header = rows[0].keys()
    assert "password_hash" not in header
    assert "token_version" not in header
    assert not [name for name in header if name.endswith("storage_key")]


def test_only_administrators_can_export(client: TestClient, admin: User) -> None:
    make_owner("03990302")
    owner = sign_in(client, "03990302")

    assert client.get("/api/admin/export/users.csv", headers=owner).status_code == 403
    assert client.get("/api/admin/export/users.csv").status_code == 401
    assert (
        client.get("/api/admin/export/secrets.csv", headers=admin_headers(client)).status_code
        == 422
    )


@pytest.mark.parametrize(
    "typed", ['=HYPERLINK("https://evil.example","x")', "+cmd", "-2+3", "@SUM(A1)", "\tx"]
)
def test_text_that_a_spreadsheet_would_run_is_exported_as_text(typed: str) -> None:
    """Every text column was typed by someone outside: a shop name starting
    with = must not become a formula on the administrator's machine."""
    from app.api.v1.admin.export import _cell

    assert _cell(typed) == f"'{typed}"


def test_ordinary_values_are_exported_unchanged() -> None:
    from decimal import Decimal

    from app.api.v1.admin.export import _cell

    assert _cell("Abu Ali Sweets") == "Abu Ali Sweets"
    # A number is never a formula; a negative one must stay a number.
    assert _cell(-35.2) == "-35.2"
    assert _cell(Decimal("1.50")) == "1.50"


def test_partner_requests_export_holds_open_and_solved_alike(
    client: TestClient, admin: User, db: Session
) -> None:
    """The owners asked for every partnership request in a sheet; a solved
    one is archived rather than gone, so it is in the file too."""
    import datetime as dt

    from app.models.partner import PartnerRequest

    db.add_all(
        [
            PartnerRequest(name="Open", phone="+9613990401", occupation="o", residence="r", offer="x"),
            PartnerRequest(
                name="Solved",
                phone="+9613990402",
                occupation="o",
                residence="r",
                offer="y",
                solved_at=dt.datetime.now(dt.UTC),
            ),
        ]
    )
    db.commit()

    response = client.get("/api/admin/export/partners.csv", headers=admin_headers(client))
    rows = _read(response.content)
    assert {row["name"] for row in rows} == {"Open", "Solved"}
    assert {"phone", "offer", "solved_at"} <= set(rows[0])
