"""Services with prices, and the services page's "best match" order (the owners'
services redesign, 3 Nov 2026)."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import BusinessStatus, TalentKind, VerificationDocumentKind
from app.models.talent import TalentServiceOffer
from app.models.taxonomy import Location
from app.services import telegram_archive
from tests.conftest import sign_in
from tests.test_candidate_directory import _attach, _candidate


def test_the_owner_prices_each_service_and_visitors_see_it(
    client: TestClient, db: Session, location: Location
) -> None:
    profile = _candidate(db, location, "03971001", kind=TalentKind.SERVICE)
    headers = sign_in(client, "03971001")
    saved = client.put(
        "/api/my/talent",
        headers=headers,
        json={
            "service_offers": [
                {"title": "Lesson", "price_from": "20", "price_to": "30", "price_unit": "hour"},
                {"title": "Exam prep", "price_from": "15"},
                {"title": "Home visit", "price_from": "900000", "currency": "LBP"},
                {"title": "Advice", "description": "Free first call"},
                # A "to" alone is the single price; equal ends are one price.
                {"title": "Notes", "price_to": "5"},
                {"title": "Course", "price_from": "50", "price_to": "50"},
            ]
        },
    )
    assert saved.status_code == 200, saved.text
    offers = saved.json()["service_offers"]
    assert [o["title"] for o in offers] == [
        "Lesson",
        "Exam prep",
        "Home visit",
        "Advice",
        "Notes",
        "Course",
    ]
    assert (offers[4]["price_from"], offers[4]["price_to"]) == ("5.00", None)
    assert (offers[5]["price_from"], offers[5]["price_to"]) == ("50.00", None)

    public = client.get(f"/api/talent/{profile.slug}").json()
    assert public["service_offers"][0]["price_unit"] == "hour"
    # The card's "from": the lowest dollar price, not the lira figure.
    [card] = [
        c
        for c in client.get("/api/talent?kind=SERVICE").json()["items"]
        if c["id"] == str(profile.id)
    ]
    assert (card["starting_price"], card["starting_price_currency"]) == ("5.00", "USD")

    # Saving again replaces the list; omitting it keeps it.
    client.put("/api/my/talent", headers=headers, json={"bio": "Twenty years teaching."})
    assert len(client.get(f"/api/talent/{profile.slug}").json()["service_offers"]) == 6
    client.put("/api/my/talent", headers=headers, json={"service_offers": []})
    body = client.get(f"/api/talent/{profile.slug}").json()
    assert body["service_offers"] == [] and body["starting_price"] is None


def test_a_backwards_range_and_a_negative_price_are_refused(
    client: TestClient, db: Session, location: Location
) -> None:
    _candidate(db, location, "03971002", kind=TalentKind.SERVICE, status=BusinessStatus.DRAFT)
    headers = sign_in(client, "03971002")
    for offer in (
        {"title": "Lesson", "price_from": "30", "price_to": "20"},
        {"title": "Lesson", "price_from": "-1"},
        {"title": "", "price_from": "10"},
    ):
        response = client.put("/api/my/talent", headers=headers, json={"service_offers": [offer]})
        assert response.status_code == 422, offer
    assert db.query(TalentServiceOffer).count() == 0


def test_best_puts_rated_verified_and_priced_providers_first(
    client: TestClient, db: Session, location: Location
) -> None:
    bare = _candidate(db, location, "03971010", kind=TalentKind.SERVICE, name="Bare")
    priced = _candidate(db, location, "03971011", kind=TalentKind.SERVICE, name="Priced")
    priced.service_offers.append(TalentServiceOffer(title="Repair", price_from=Decimal(10)))
    verified = _candidate(db, location, "03971012", kind=TalentKind.SERVICE, name="Verified")
    _attach(db, verified, VerificationDocumentKind.IDENTITY)
    # One five-star review weighs less than many good ones.
    _candidate(
        db,
        location,
        "03971013",
        kind=TalentKind.SERVICE,
        name="Lucky",
        rating_average=Decimal(5),
        rating_count=1,
    )
    _candidate(
        db,
        location,
        "03971014",
        kind=TalentKind.SERVICE,
        name="Proven",
        rating_average=Decimal("4.6"),
        rating_count=12,
    )
    db.commit()

    names = [
        card["display_name"]
        for card in client.get("/api/talent?kind=SERVICE&sort=best").json()["items"]
    ]
    assert names == ["Proven", "Verified", "Lucky", "Priced", "Bare"]
    # Newest stays the default.
    newest = client.get("/api/talent?kind=SERVICE").json()["items"]
    assert newest[0]["display_name"] == "Proven" and newest[-1]["id"] == str(bare.id)


def test_offers_are_archived_like_the_rest_of_a_profile() -> None:
    assert "talent_service_offers" in telegram_archive.ARCHIVED_TABLES


def test_the_owner_answers_questions_and_visitors_read_them(
    client: TestClient, db: Session, location: Location
) -> None:
    profile = _candidate(db, location, "03971020", kind=TalentKind.SERVICE)
    headers = sign_in(client, "03971020")
    saved = client.put(
        "/api/my/talent",
        headers=headers,
        json={
            "faqs": [
                {"question": " Do you travel? ", "answer": "Across the South."},
                {"question": "Do you invoice?", "answer": "Yes."},
            ]
        },
    )
    assert saved.status_code == 200, saved.text
    public = client.get(f"/api/talent/{profile.slug}").json()
    assert [f["question"] for f in public["faqs"]] == ["Do you travel?", "Do you invoice?"]

    empty = client.put(
        "/api/my/talent", headers=headers, json={"faqs": [{"question": "Q", "answer": ""}]}
    )
    assert empty.status_code == 422
    assert "talent_faqs" in telegram_archive.ARCHIVED_TABLES
