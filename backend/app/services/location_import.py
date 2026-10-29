"""Bring the location tree up to the owners' full list of Lebanon's towns.

``scripts/data/lebanon_towns.json`` holds every governorate, district and
town (the owners' spreadsheet of 29 Oct 2026). The tree already in the
database grew by hand: towns added one at a time, some filed under the wrong
district, two districts entered twice, spellings that differ from the list.
Listings point at those rows, so the import works *around* them rather than
replacing them:

- an existing row the list recognises keeps its id, slug and spelling, and is
  moved under the district the list gives it;
- a district entered twice is merged into one, its towns and listings moved
  to the survivor;
- a town the list does not have is kept if anything points at it, and
  otherwise hidden (``is_active`` off), never deleted;
- everything else on the list is added.

Matching is by a normalised name (hamza forms, taa marbuta, alif maqsura, the
article and spaces ignored), and only within the same governorate -- or
within the South and Nabatieh together, which hand-entered rows often
confused. A town name the list has more than once is matched only where the
district settles it. Anything less certain is left alone.

It runs once per deployment database (the ``locations_import`` key in
``site_settings`` records it), because a second pass would hide a town an
administrator added after the first.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.business import Business
from app.models.enums import LocationType
from app.models.job import JobOpening
from app.models.site_setting import SiteSetting
from app.models.talent import TalentProfile
from app.models.taxonomy import Location
from app.models.workshop import Workshop
from app.services.slug import slugify_name

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parents[2] / "scripts" / "data" / "lebanon_towns.json"
DONE_KEY = "locations_import"
DONE_VALUE = "v1"

#: Every table with a ``location_id``: what makes a row "in use", and what a
#: merge has to move.
REFERENCING = (Business, TalentProfile, Article, Workshop, JobOpening)

# Code points rather than letters: no Arabic text in source (test_i18n.py).
_ALIF, _LAM = 0x0627, 0x0644
_FOLD = {
    0x0623: _ALIF,  # alif with hamza above
    0x0625: _ALIF,  # alif with hamza below
    0x0622: _ALIF,  # alif madda
    0x0649: 0x064A,  # alif maqsura -> yaa
    0x0629: 0x0647,  # taa marbuta -> haa
    0x0624: 0x0648,  # waw with hamza -> waw
    0x0626: 0x064A,  # yaa with hamza -> yaa
    0x0640: None,  # tatweel
    **{code: None for code in range(0x064B, 0x0653)},  # short vowels
}
_ARTICLE = re.compile(r"(^|\s)" + chr(_ALIF) + chr(_LAM))


def normalise(name: str) -> str:
    """A spelling-insensitive key for an Arabic place name."""
    text = name.strip().translate(_FOLD)
    text = _ARTICLE.sub(r"\1", text)
    return re.sub(r"[\s\-]", "", text)


@dataclass
class ImportReport:
    governorates_added: int = 0
    districts_added: int = 0
    districts_merged: int = 0
    towns_added: int = 0
    towns_moved: int = 0
    towns_merged: int = 0
    towns_hidden: int = 0
    towns_kept_unlisted: list[str] = field(default_factory=list)
    moved: list[tuple[str, str, str]] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"governorates +{self.governorates_added}, districts +{self.districts_added} "
            f"(merged {self.districts_merged}), towns +{self.towns_added}, "
            f"moved {self.towns_moved}, merged {self.towns_merged}, hidden {self.towns_hidden}, "
            f"kept though unlisted {len(self.towns_kept_unlisted)}"
        )


def already_done(db: Session) -> bool:
    return db.get(SiteSetting, DONE_KEY) is not None


def load_data(path: Path = DATA_FILE) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


class _Tree:
    """The location rows, indexed for the import, with the writes it needs."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.rows: list[Location] = list(db.execute(select(Location)).scalars())
        self.by_id = {row.id: row for row in self.rows}
        self.slugs = {row.slug for row in self.rows}
        self.used: set[uuid.UUID] = set()
        for model in REFERENCING:
            column = model.location_id  # type: ignore[attr-defined]
            found = db.execute(select(column).where(column.is_not(None)).distinct()).scalars()
            self.used.update(value for value in found if value is not None)

    def governorate_of(self, row: Location) -> Location | None:
        node: Location | None = row
        while node is not None and node.type is not LocationType.GOVERNORATE:
            node = self.by_id.get(node.parent_id) if node.parent_id else None
        return node

    def district_of(self, row: Location) -> Location | None:
        parent = self.by_id.get(row.parent_id) if row.parent_id else None
        return parent if parent is not None and parent.type is LocationType.DISTRICT else None

    def add(self, name: str, kind: LocationType, parent: Location | None, order: int) -> Location:
        slug = slugify_name(name, fallback_prefix="place")
        base, n = slug, 2
        while slug in self.slugs:
            slug, n = f"{base}-{n}", n + 1
        self.slugs.add(slug)
        row = Location(
            id=uuid.uuid4(),
            name_ar=name,
            slug=slug,
            type=kind,
            parent_id=parent.id if parent else None,
            sort_order=order,
            is_active=True,
        )
        self.db.add(row)
        self.rows.append(row)
        self.by_id[row.id] = row
        return row

    def merge(self, loser: Location, survivor: Location) -> None:
        """Move everything that points at ``loser`` onto ``survivor``, then hide it."""
        for model in REFERENCING:
            column = model.location_id  # type: ignore[attr-defined]
            self.db.execute(
                update(model).where(column == loser.id).values(location_id=survivor.id)
            )
        for child in self.rows:
            if child.parent_id == loser.id:
                child.parent_id = survivor.id
        if loser.id in self.used:
            self.used.add(survivor.id)
        loser.is_active = False


def import_locations(db: Session, data: dict[str, Any] | None = None) -> ImportReport:
    """Apply the list to the tree. The caller commits."""
    data = data or load_data()
    # Wait at most this long for a row another connection holds, rather than
    # hanging silently: the first attempt on the live database did exactly
    # that, and a lock timeout turns it into an error that names the wait.
    db.execute(text("SET LOCAL lock_timeout = '15s'"))
    db.execute(text("SET LOCAL statement_timeout = '60s'"))
    tree = _Tree(db)
    logger.info("Location import: %d rows loaded, %d in use", len(tree.rows), len(tree.used))
    report = ImportReport()
    # Governorates matched as one region (the file's ``match_together``).
    together = {normalise(name) for name in data.get("match_together", [])}

    def _region(governorate_key: str) -> str:
        return "together" if governorate_key in together else governorate_key

    children: dict[uuid.UUID, int] = defaultdict(int)
    for row in tree.rows:
        if row.parent_id:
            children[row.parent_id] += 1

    def rows_of(kind: LocationType) -> list[Location]:
        return [row for row in tree.rows if row.type is kind]

    def usage(row: Location) -> int:
        return int(row.id in tree.used) + children[row.id]

    # --- Governorates -------------------------------------------------------
    governorates: dict[str, Location] = {}
    for gov in rows_of(LocationType.GOVERNORATE):
        key = normalise(gov.name_ar)
        if key in governorates:
            tree.merge(gov, governorates[key])
        else:
            governorates[key] = gov
    for order, entry in enumerate(data["governorates"]):
        key = normalise(entry["name_ar"])
        if key not in governorates:
            governorates[key] = tree.add(entry["name_ar"], LocationType.GOVERNORATE, None, order)
            report.governorates_added += 1
        governorates[key].is_active = True
    # Parents exist before anything points at them: the rows refer to each
    # other by id, which the unit of work cannot order on its own.
    db.flush()

    logger.info("Location import: governorates ready")

    # --- Districts: merge the doubles, then put each under its governorate --
    districts: dict[str, Location] = {}
    by_key: dict[str, list[Location]] = defaultdict(list)
    for district in rows_of(LocationType.DISTRICT):
        by_key[normalise(district.name_ar)].append(district)
    for key, group in by_key.items():
        group.sort(key=lambda row: (row.is_active, usage(row)), reverse=True)
        survivor, *doubles = group
        for double in doubles:
            if double.is_active:
                tree.merge(double, survivor)
                report.districts_merged += 1
        districts[key] = survivor

    listed: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for gov_entry in data["governorates"]:
        gov = governorates[normalise(gov_entry["name_ar"])]
        for order, entry in enumerate(gov_entry["districts"]):
            key = normalise(entry["name_ar"])
            if key not in districts:
                districts[key] = tree.add(entry["name_ar"], LocationType.DISTRICT, gov, order)
                report.districts_added += 1
            district = districts[key]
            district.parent_id = gov.id
            district.is_active = True
            for town in entry["towns"]:
                listed[normalise(town)].append(
                    (normalise(gov_entry["name_ar"]), key, town)
                )

    db.flush()
    logger.info("Location import: districts ready (%d merged)", report.districts_merged)

    # --- Towns: match what exists, add the rest -----------------------------
    claimed: dict[tuple[str, str], Location] = {}  # (district key, town key) -> row
    leftovers: list[Location] = []
    # Active rows first, then the most used: they are the ones that survive.
    for town in sorted(
        rows_of(LocationType.TOWN), key=lambda row: (row.is_active, usage(row)), reverse=True
    ):
        key = normalise(town.name_ar)
        town_gov = tree.governorate_of(town)
        region = _region(normalise(town_gov.name_ar)) if town_gov else None
        current = tree.district_of(town)
        current_key = normalise(current.name_ar) if current else None
        candidates = [
            entry for entry in listed.get(key, []) if region is None or _region(entry[0]) == region
        ]
        in_district = [entry for entry in candidates if entry[1] == current_key]
        chosen = in_district or (candidates if len(candidates) == 1 else [])
        if not chosen:
            leftovers.append(town)
            continue
        _, district_key, _ = chosen[0]
        slot = (district_key, key)
        if slot in claimed:
            # The same town entered twice: one row survives.
            if town.is_active:
                tree.merge(town, claimed[slot])
                report.towns_merged += 1
            continue
        claimed[slot] = town
        target = districts[district_key]
        if town.parent_id != target.id:
            report.moved.append((town.name_ar, current.name_ar if current else "", target.name_ar))
            town.parent_id = target.id
            report.towns_moved += 1
        town.is_active = True

    logger.info(
        "Location import: %d towns matched, %d moved", len(claimed), report.towns_moved
    )
    for gov_entry in data["governorates"]:
        for entry in gov_entry["districts"]:
            district_key = normalise(entry["name_ar"])
            for order, name in enumerate(entry["towns"]):
                slot = (district_key, normalise(name))
                if slot not in claimed:
                    claimed[slot] = tree.add(
                        name, LocationType.TOWN, districts[district_key], order
                    )
                    report.towns_added += 1

    for town in leftovers:
        if town.is_active is False:
            continue
        if town.id in tree.used:
            report.towns_kept_unlisted.append(town.name_ar)
        else:
            town.is_active = False
            report.towns_hidden += 1

    db.flush()
    logger.info("Location import: %d towns added, flushed", report.towns_added)
    return report


def run_once(db: Session) -> ImportReport | None:
    """Import unless this database already has; records it and commits."""
    if already_done(db):
        return None
    logger.info("Location import: starting")
    report = import_locations(db)
    db.add(SiteSetting(key=DONE_KEY, value=DONE_VALUE))
    db.commit()
    logger.info("Location list imported: %s", report.summary())
    if report.towns_kept_unlisted:
        logger.info(
            "Kept because listings use them: %s", ", ".join(report.towns_kept_unlisted)
        )
    return report


def count_active_towns(db: Session) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(Location)
            .where(Location.type == LocationType.TOWN, Location.is_active.is_(True))
        ).scalar_one()
    )
