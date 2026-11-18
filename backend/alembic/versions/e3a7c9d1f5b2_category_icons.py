"""Icons for the categories staff added without one (the owners' request,
18 Nov 2026).

The admin had no icon picker, so every category added there showed a
plain tag on the products page. This fills the icon only where it is
empty, by slug: a category that already has one keeps it, and a slug
that is not on this list is left alone. Data only, no schema change.

Revision ID: e3a7c9d1f5b2
Revises: d2f6b8a1c3e9
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e3a7c9d1f5b2"
down_revision = "d2f6b8a1c3e9"
branch_labels = None
depends_on = None

ICONS = {
    "مونة-جنوبية": "cooking-pot",
    "كروشيه": "scissors",
    "هدايا-وأكسسوارات-2": "gift",
    "كتب-وقرطاسي-ة": "book-open",
    "ديكور-منزل-ولوحات": "frame",
    "فخار-وشموع": "flame",
    "عسل": "hexagon",
    "زبدة-ومرب-ى": "cherry",
    "إسلامي-ات": "moon",
    "خرضوات": "wrench",
    "أحجار-كريمة": "gem",
    "بلاط-وحجر": "brick-wall",
    "أكسسورات-هواتف": "smartphone",
    "مواد-تنظيف-منزلية": "spray-can",
    "هدايا-أطفال": "baby",
    "نجارة-وخشب": "axe",
    "سج-اد-وفرش-منزل": "armchair",
    "بيع-انظمة-الطاقة-الشمسية": "sun",
    "توزيع-إنترنت": "wifi",
    "خدمة-توصيل-ديلفري": "truck",
    "دروس-خصوصية": "graduation-cap",
}


def upgrade() -> None:
    statement = sa.text(
        "UPDATE categories SET icon = :icon "
        "WHERE slug = :slug AND (icon IS NULL OR icon = '')"
    )
    for slug, icon in ICONS.items():
        op.execute(statement.bindparams(slug=slug, icon=icon))


def downgrade() -> None:
    # Nothing to undo safely: an icon may have been changed since.
    pass
