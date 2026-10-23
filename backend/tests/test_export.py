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

from app.models.user import User
from tests.conftest import admin_headers, make_owner, sign_in

DATASETS = ["businesses", "products", "users", "talent", "orders"]


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
