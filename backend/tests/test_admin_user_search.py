"""Finding an account from the admin list: by phone however it is typed, by
name (the account's own, or its shop's), by role and status, in a chosen
order."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.taxonomy import Category, Location
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar


def _ids(client: TestClient, **query: str) -> list[str]:
    response = client.get("/api/admin/users", headers=admin_headers(client), params=query)
    assert response.status_code == 200, response.text
    return [row["id"] for row in response.json()["items"]]


def _user(db: Session, phone: str) -> User:
    user = db.query(User).filter(User.phone_number.contains(phone[-6:])).one()
    return user


def test_search_by_phone_in_any_format(client: TestClient, db: Session, admin: User) -> None:
    sign_in(client, "03123987")
    sign_in(client, "70555111")
    target = _user(db, "03123987")

    for typed in ("03123987", "03 123 987", "+961 3 123987", "3123987", "123987"):
        assert _ids(client, q=typed) == [str(target.id)], typed


def test_search_by_name_or_by_the_shop_it_owns(
    client: TestClient, db: Session, admin: User, category: Category, location: Location
) -> None:
    headers = sign_in(client, "03123401")
    owner = _user(db, "03123401")
    owner.display_name = ar("business.second")
    db.commit()
    other = sign_in(client, "03123402")
    created = client.post(
        "/api/businesses",
        headers=other,
        json={
            "name": ar("business.first"),
            "category_id": str(category.id),
            "location_id": str(location.id),
        },
    )
    assert created.status_code == 201, created.text
    shop_owner = _user(db, "03123402")
    assert headers

    assert _ids(client, q=ar("business.second")) == [str(owner.id)]
    assert _ids(client, q=ar("business.first")) == [str(shop_owner.id)]


def test_filters_and_order(client: TestClient, db: Session, admin: User) -> None:
    sign_in(client, "03123501")
    sign_in(client, "03123502")
    older, newer = _user(db, "03123501"), _user(db, "03123502")
    older.created_at = datetime.now(UTC) - timedelta(days=30)
    newer.is_active = False
    db.commit()

    owners = _ids(client, role="OWNER")
    assert str(admin.id) not in owners and {str(older.id), str(newer.id)} <= set(owners)
    assert _ids(client, role="ADMIN") == [str(admin.id)]
    assert _ids(client, active="false") == [str(newer.id)]
    newest_first = _ids(client, role="OWNER")
    oldest_first = _ids(client, role="OWNER", sort="oldest")
    assert newest_first[-1] == str(older.id) and oldest_first[0] == str(older.id)
    assert client.get(
        "/api/admin/users", headers=admin_headers(client), params={"sort": "nope"}
    ).status_code == 422
