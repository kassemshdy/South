"""The one-time import of the owners' full town list.

What it must never do is break a listing: a row something points at keeps its
id and stays visible, wherever it ends up. Names here are Latin on purpose --
the matching is about structure, and the real Arabic list is exercised by
``test_the_real_list_loads``.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import BusinessStatus, LocationType
from app.models.site_setting import SiteSetting
from app.models.taxonomy import Location
from app.services import location_import
from tests.conftest import make_owner

DATA = {
    "match_together": ["South", "Nabatieh"],
    "governorates": [
        {
            "name_ar": "South",
            "districts": [{"name_ar": "Tyre", "towns": ["Qana", "Burj"]}],
        },
        {
            "name_ar": "Nabatieh",
            "districts": [
                {"name_ar": "Nabatieh", "towns": ["Kfarroummane"]},
                {"name_ar": "Marjayoun", "towns": ["Khiam", "Qlayaa"]},
            ],
        },
        {
            "name_ar": "Mount Lebanon",
            "districts": [{"name_ar": "Chouf", "towns": ["Jbaa", "Deir"]}],
        },
    ],
}


def _loc(db: Session, name: str, kind: LocationType, parent: Location | None = None) -> Location:
    row = Location(
        id=uuid.uuid4(),
        name_ar=name,
        slug=f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:4]}",
        type=kind,
        parent_id=parent.id if parent else None,
    )
    db.add(row)
    db.flush()
    return row


def _shop_in(db: Session, location: Location, phone: str) -> Business:
    owner = make_owner(phone)
    shop = Business(
        name=f"Shop {phone}",
        slug=f"shop-{phone}",
        owner_id=owner.id,
        location_id=location.id,
        status=BusinessStatus.APPROVED,
    )
    db.add(shop)
    db.flush()
    return shop


def _by_name(db: Session, name: str, kind: LocationType) -> list[Location]:
    return list(
        db.execute(select(Location).where(Location.name_ar == name, Location.type == kind))
        .scalars()
    )


def test_existing_rows_keep_their_ids_and_move_to_the_right_district(db: Session) -> None:
    south = _loc(db, "South", LocationType.GOVERNORATE)
    nabatieh = _loc(db, "Nabatieh", LocationType.GOVERNORATE)
    tyre = _loc(db, "Tyre", LocationType.DISTRICT, south)
    nab_district = _loc(db, "Nabatieh", LocationType.DISTRICT, nabatieh)
    # Misfiled under Nabatieh, and a shop is there.
    khiam = _loc(db, "Khiam", LocationType.TOWN, nab_district)
    shop = _shop_in(db, khiam, "03980001")
    qana = _loc(db, "Qana", LocationType.TOWN, tyre)
    db.commit()

    report = location_import.import_locations(db, DATA)
    db.commit()

    db.refresh(khiam)
    marjayoun = _by_name(db, "Marjayoun", LocationType.DISTRICT)[0]
    assert khiam.parent_id == marjayoun.id and khiam.is_active
    assert db.get(Business, shop.id).location_id == khiam.id  # type: ignore[union-attr]
    db.refresh(qana)
    assert qana.parent_id == tyre.id
    # Everything on the list exists once, the existing rows not duplicated.
    assert len(_by_name(db, "Khiam", LocationType.TOWN)) == 1
    assert len(_by_name(db, "Burj", LocationType.TOWN)) == 1
    assert len(_by_name(db, "Chouf", LocationType.DISTRICT)) == 1
    assert report.governorates_added == 1  # Mount Lebanon


def test_a_district_entered_twice_is_merged_with_its_towns_and_listings(db: Session) -> None:
    nabatieh = _loc(db, "Nabatieh", LocationType.GOVERNORATE)
    first = _loc(db, "Marjayoun", LocationType.DISTRICT, nabatieh)
    second = _loc(db, "Marjayoun", LocationType.DISTRICT, nabatieh)
    town = _loc(db, "Qlayaa", LocationType.TOWN, second)
    district_shop = _shop_in(db, second, "03980002")
    _loc(db, "Khiam", LocationType.TOWN, first)
    db.commit()

    report = location_import.import_locations(db, DATA)
    db.commit()

    assert report.districts_merged == 1
    active = [d for d in _by_name(db, "Marjayoun", LocationType.DISTRICT) if d.is_active]
    assert len(active) == 1
    db.refresh(town)
    assert town.parent_id == active[0].id
    assert db.get(Business, district_shop.id).location_id == active[0].id  # type: ignore[union-attr]


def test_an_unlisted_town_is_hidden_unless_something_uses_it(db: Session) -> None:
    south = _loc(db, "South", LocationType.GOVERNORATE)
    tyre = _loc(db, "Tyre", LocationType.DISTRICT, south)
    unused = _loc(db, "Nowhere", LocationType.TOWN, tyre)
    used = _loc(db, "Somewhere", LocationType.TOWN, tyre)
    _shop_in(db, used, "03980003")
    db.commit()

    report = location_import.import_locations(db, DATA)
    db.commit()

    db.refresh(unused)
    db.refresh(used)
    assert unused.is_active is False  # hidden, never deleted
    assert used.is_active is True and used.parent_id == tyre.id
    assert report.towns_kept_unlisted == ["Somewhere"]


def test_a_southern_town_is_never_matched_to_a_namesake_elsewhere(db: Session) -> None:
    """Jbaa in Nabatieh is not Jbaa in the Chouf: same name, other region."""
    nabatieh = _loc(db, "Nabatieh", LocationType.GOVERNORATE)
    district = _loc(db, "Nabatieh", LocationType.DISTRICT, nabatieh)
    jbaa = _loc(db, "Jbaa", LocationType.TOWN, district)
    _shop_in(db, jbaa, "03980004")
    db.commit()

    location_import.import_locations(db, DATA)
    db.commit()

    db.refresh(jbaa)
    assert jbaa.parent_id == district.id
    chouf_jbaa = [t for t in _by_name(db, "Jbaa", LocationType.TOWN) if t.id != jbaa.id]
    assert len(chouf_jbaa) == 1


def test_it_runs_once_per_database(db: Session) -> None:
    south = _loc(db, "South", LocationType.GOVERNORATE)
    db.commit()
    first = location_import.run_once(db)
    assert first is not None
    assert db.get(SiteSetting, location_import.DONE_KEY) is not None
    # An administrator re-activates a hidden town, or adds one: never undone.
    added = _loc(db, "Added by hand", LocationType.TOWN, south)
    db.commit()
    assert location_import.run_once(db) is None
    db.refresh(added)
    assert added.is_active


def test_the_real_list_loads(client: TestClient, db: Session) -> None:
    data = location_import.load_data()
    assert len(data["governorates"]) == 9
    assert sum(len(g["districts"]) for g in data["governorates"]) == 26

    location_import.import_locations(db, data)
    db.commit()
    assert location_import.count_active_towns(db) == 1704
    listed = client.get("/api/locations").json()
    assert sum(1 for row in listed if row["type"] == "TOWN") == 1704
