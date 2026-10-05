"""A business owner may keep the listing's numbers off the public page.

The owners asked that everyone listing give a number and choose whether the
public sees it. Hidden numbers must be absent from every public payload —
the listing, the directory, a product's seller block and the share tags —
while the owner still reads and edits them.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from tests.conftest import sign_in
from tests.samples import ar

NUMBER = "+9613960201"


def test_a_business_with_private_numbers_publishes_none_of_them(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(client, "03960200")
    created = client.post(
        "/api/businesses",
        headers=headers,
        json={
            "name": ar("business.manakish"),
            "short_description": ar("business.manakish_short"),
            "category_id": str(category.id),
            "location_id": str(location.id),
            "phone": NUMBER,
            "whatsapp": NUMBER,
            "phone_public": False,
        },
    )
    assert created.status_code == 201, created.text
    business = created.json()
    assert business["phone_public"] is False
    # The owner's own view keeps the numbers, so the form can show them.
    assert business["whatsapp"] == NUMBER

    client.post(
        f"/api/businesses/{business['id']}/items",
        headers=headers,
        json={"title": ar("item.generic"), "price": "1.00", "currency": "USD"},
    )
    record = db.get(Business, business["id"])
    assert record is not None
    record.status = BusinessStatus.APPROVED
    db.commit()

    public = client.get(f"/api/businesses/{business['slug']}").json()
    assert public["phone"] is None
    assert public["whatsapp"] is None
    products = client.get("/api/items").json()["items"]
    assert [row["business"]["whatsapp"] for row in products] == [None]
    assert NUMBER not in client.get(f"/business/{business['slug']}").text

    # Shown again the moment the owner says so.
    client.put(f"/api/businesses/{business['id']}", headers=headers, json={"phone_public": True})
    assert client.get(f"/api/businesses/{business['slug']}").json()["whatsapp"] == NUMBER
