"""Every seller pins themselves on the map, and visitors can sort by distance.

The owners made the pin compulsory for every seller -- the town is enough --
and asked for the directories to put the nearest first when a visitor shares
their position. The position is the visitor's own and travels in a query
string, so the access log must not keep it.
"""

from __future__ import annotations

import logging

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.logging import DropQueryString
from app.models.business import Business
from app.models.enums import BusinessStatus
from app.models.taxonomy import Category, Location
from tests.conftest import sign_in
from tests.samples import ar

TYRE = (33.27, 35.2)
SAIDA = (33.56, 35.37)


def _business(
    client: TestClient,
    headers: dict[str, str],
    category: Category,
    location: Location,
    name: str,
    pin: tuple[float, float] | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": name,
        "short_description": ar("business.generic_short"),
        "category_id": str(category.id),
        "location_id": str(location.id),
        "whatsapp": "+9613960210",
    }
    if pin is not None:
        payload["latitude"], payload["longitude"] = pin
    created = client.post("/api/businesses", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    result: dict[str, object] = created.json()
    return result


def test_a_listing_without_a_pin_is_not_ready_for_review(
    client: TestClient, category: Category, location: Location
) -> None:
    headers = sign_in(client, "03960210")
    business = _business(client, headers, category, location, ar("business.first"), None)
    readiness = client.get(f"/api/businesses/{business['id']}/readiness", headers=headers)
    assert "business.field.map_pin" in readiness.json()

    client.put(
        f"/api/businesses/{business['id']}",
        headers=headers,
        json={"latitude": TYRE[0], "longitude": TYRE[1]},
    )
    readiness = client.get(f"/api/businesses/{business['id']}/readiness", headers=headers)
    assert "business.field.map_pin" not in readiness.json()


def test_the_pin_is_published_on_the_listing(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    headers = sign_in(client, "03960211")
    business = _business(client, headers, category, location, ar("business.first"), TYRE)
    record = db.get(Business, business["id"])
    assert record is not None
    record.status = BusinessStatus.APPROVED
    db.commit()

    public = client.get(f"/api/businesses/{business['slug']}").json()
    assert (public["latitude"], public["longitude"]) == TYRE


def test_nearest_puts_the_closest_pin_first_and_the_unpinned_last(
    client: TestClient, db: Session, category: Category, location: Location
) -> None:
    rows = [
        ("03960212", ar("business.first"), SAIDA),
        ("03960213", ar("business.second_shop"), None),
        ("03960214", ar("business.manakish"), TYRE),
    ]
    for phone, name, pin in rows:
        created = _business(client, sign_in(client, phone), category, location, name, pin)
        record = db.get(Business, created["id"])
        assert record is not None
        record.status = BusinessStatus.APPROVED
    db.commit()

    def order(lat: float, lng: float) -> list[str]:
        response = client.get(f"/api/businesses?sort=nearest&lat={lat}&lng={lng}")
        assert response.status_code == 200, response.text
        return [row["name"] for row in response.json()["items"]]

    # Standing in Tyre, then in Saida: the pinned two swap, the unpinned one
    # stays last either way.
    assert order(*TYRE) == [ar("business.manakish"), ar("business.first"), ar("business.second_shop")]
    assert order(*SAIDA) == [ar("business.first"), ar("business.manakish"), ar("business.second_shop")]

    # Without a position, nearest is simply newest -- never an error.
    fallback = client.get("/api/businesses?sort=nearest")
    assert fallback.status_code == 200
    assert fallback.json()["items"][0]["name"] == ar("business.manakish")

    # Products and profiles take the same parameters.
    assert client.get(f"/api/items?sort=nearest&lat={TYRE[0]}&lng={TYRE[1]}").status_code == 200
    assert client.get(f"/api/talent?sort=nearest&lat={TYRE[0]}&lng={TYRE[1]}").status_code == 200


def test_the_access_log_keeps_the_path_and_drops_the_query() -> None:
    """A visitor's position and search terms never reach the deployment logs."""
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        0,
        '%s - "%s %s HTTP/%s" %d',
        ("10.0.0.1:5000", "GET", "/api/businesses?sort=nearest&lat=33.27&lng=35.2", "1.1", 200),
        None,
    )
    assert DropQueryString().filter(record)
    message = record.getMessage()
    assert "/api/businesses" in message
    assert "33.27" not in message
    assert "?" not in message
