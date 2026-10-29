"""The admin growth report, computed from the live data on every request.

The owners asked for the growth plan's analysis -- Alex Hormozi's value
equation, Value = (Dream outcome x Likelihood) / (Time delay x Effort) --
read off real numbers, with the next steps that follow from them. Nothing
here is stored: opening the page is what computes it, so it can never be a
stale copy of a spreadsheet.

The question it is built around is the plan's constraint, "did a seller get
a customer this week?", which is why orders lead and views follow. Views are
page opens, never people: the counter stores nothing about a visitor (see
``app/models/analytics.py``), so no label may call them visitors.

Everything is an aggregate or a shop's public name. No customer's name or
phone and no owner's identity is read, so the report is safe for every
staff role to see.
"""

from __future__ import annotations

import statistics
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.models.analytics import ListingViewDaily
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus, Currency, TestimonialStatus, ViewSubject
from app.models.order import Order, OrderLine
from app.models.service_request import ServiceRequest
from app.models.site_setting import SiteSetting
from app.models.talent import TalentProfile
from app.models.testimonial import Testimonial
from app.repositories.item import ItemRepository
from app.schemas.growth_report import (
    DEFAULT_GOAL_USD,
    GrowthPlanIn,
    GrowthPlanOut,
    GrowthReportOut,
    OfferPopupOut,
    Recommendation,
    SellerHealth,
    ShopLine,
    WeeklySeries,
)

WEEKS = 8
#: The plan promises a page within 48 hours of applying.
PROMISED_HOURS = 48
#: Below this share of shops with an order, proof is the weakest lever.
PROOF_SHARE = 0.3
#: A shop with fewer public products than this looks empty to a buyer.
THIN_CATALOGUE = 3
#: Enough published testimonials that a newcomer sees social proof.
TESTIMONIAL_TARGET = 10
SHOWN_SHOPS = 5
GOAL_KEY = "growth_goal_usd"
OFFER_KEY = "growth_offer"
POPUP_KEY = "growth_offer_popup"
SHOWN_QUIET = 10

_PRIORITY = {"high": 0, "medium": 1, "low": 2}


def _start_of(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


class GrowthReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build(self, now: datetime | None = None) -> GrowthReportOut:
        now = now or datetime.now(UTC)
        today = now.date()
        # Seven-day windows ending today, so the last bar is "this week" as
        # the plan's weekly question means it, whatever the weekday.
        week_starts = [today - timedelta(days=7 * (WEEKS - index) - 1) for index in range(WEEKS)]
        since_7 = _start_of(today - timedelta(days=6))
        since_30 = _start_of(today - timedelta(days=29))

        approved = list(
            self.db.execute(
                select(Business.id, Business.name, Business.slug, Business.logo_url).where(
                    Business.status == BusinessStatus.APPROVED
                )
            ).all()
        )
        approved_ids = {row.id for row in approved}

        orders_30 = self._orders_by_shop(since_30)
        orders_7 = self._orders_by_shop(since_7)
        views_30 = self._views_by_shop(today - timedelta(days=29))
        products = self._public_products_by_shop()

        with_orders = viewed = unseen = 0
        lines: list[ShopLine] = []
        quiet: list[ShopLine] = []
        for row in approved:
            line = ShopLine(
                name=row.name,
                slug=row.slug,
                orders=orders_30.get(row.id, 0),
                views=views_30.get(row.id, 0),
            )
            lines.append(line)
            if line.orders:
                with_orders += 1
            elif line.views:
                viewed += 1
            else:
                unseen += 1
                quiet.append(line)

        views_total_30 = self._views_total(today - timedelta(days=29))
        orders_total_30 = sum(orders_30.values())
        weekly = WeeklySeries(
            orders=self._weekly_count(Order, week_starts),
            service_requests=self._weekly_count(ServiceRequest, week_starts),
            views=self._weekly_views(week_starts),
            new_sellers=[
                shops + talents
                for shops, talents in zip(
                    self._weekly_count(Business, week_starts),
                    self._weekly_count(TalentProfile, week_starts),
                    strict=True,
                )
            ],
            new_products=self._weekly_count(BusinessItem, week_starts),
        )

        pending, pending_late = self._pending(now)
        median_hours = self._median_approval_hours(now)
        testimonials = self._count(
            select(func.count())
            .select_from(Testimonial)
            .where(Testimonial.status == TestimonialStatus.APPROVED)
        )
        thin = sum(1 for shop_id in approved_ids if products.get(shop_id, 0) < THIN_CATALOGUE)
        no_logo = sum(1 for row in approved if not row.logo_url)

        report = GrowthReportOut(
            generated_at=now,
            goal_usd=self.plan().goal_usd,
            order_value_usd=self._order_value(Currency.USD),
            order_value_usd_30d=self._order_value(Currency.USD, since_30),
            order_value_lbp=self._order_value(Currency.LBP),
            week_starts=week_starts,
            approved_shops=len(approved),
            approved_talents=self._count(
                select(func.count())
                .select_from(TalentProfile)
                .where(TalentProfile.status == BusinessStatus.APPROVED)
            ),
            public_products=sum(products.values()),
            pending_reviews=pending,
            pending_over_48h=pending_late,
            shops_with_order_7d=sum(1 for shop_id in approved_ids if orders_7.get(shop_id)),
            shops_with_order_30d=with_orders,
            orders_7d=sum(orders_7.values()),
            orders_30d=orders_total_30,
            service_requests_30d=self._count(
                select(func.count())
                .select_from(ServiceRequest)
                .where(ServiceRequest.created_at >= since_30)
            ),
            views_30d=views_total_30,
            orders_per_1000_views=(
                round(orders_total_30 * 1000 / views_total_30, 1) if views_total_30 else None
            ),
            median_approval_hours=median_hours,
            approved_testimonials=testimonials,
            thin_catalogue_shops=thin,
            shops_without_logo=no_logo,
            weekly=weekly,
            health=SellerHealth(with_orders=with_orders, viewed_no_orders=viewed, unseen=unseen),
            top_shops=sorted(
                (line for line in lines if line.orders),
                key=lambda line: (-line.orders, -line.views, line.name),
            )[:SHOWN_SHOPS],
            quiet_shops=sorted(quiet, key=lambda line: line.name)[:SHOWN_QUIET],
            recommendations=[],
        )
        report.recommendations = recommend(report)
        return report

    # --- The goal and the offer ---------------------------------------------

    def plan(self) -> GrowthPlanOut:
        goal = self.db.get(SiteSetting, GOAL_KEY)
        offer = self.db.get(SiteSetting, OFFER_KEY)
        return GrowthPlanOut(
            goal_usd=int(goal.value) if goal and goal.value.isdigit() else DEFAULT_GOAL_USD,
            offer=offer.value if offer else None,
            offer_popup=self.db.get(SiteSetting, POPUP_KEY) is not None,
        )

    def offer_popup(self) -> OfferPopupOut:
        """The public half: the offer only while the popup is on. The goal
        stays with the staff."""
        plan = self.plan()
        if not plan.offer_popup:
            return OfferPopupOut()
        return OfferPopupOut(enabled=True, offer=plan.offer)

    def set_plan(self, payload: GrowthPlanIn) -> GrowthPlanOut:
        for key, value in (
            (GOAL_KEY, None if payload.goal_usd == DEFAULT_GOAL_USD else str(payload.goal_usd)),
            (OFFER_KEY, payload.offer),
            (POPUP_KEY, "1" if payload.offer_popup else None),
        ):
            row = self.db.get(SiteSetting, key)
            if value is None:
                if row is not None:
                    self.db.delete(row)
            elif row is None:
                self.db.add(SiteSetting(key=key, value=value))
            else:
                row.value = value
        self.db.commit()
        return self.plan()

    # --- Queries -------------------------------------------------------------

    def _order_value(self, currency: Currency, since: datetime | None = None) -> float:
        """What customers asked for, priced at the time: an order is a request
        to be contacted, so this is demand on the site, not money received."""
        stmt = (
            select(func.coalesce(func.sum(OrderLine.price * OrderLine.quantity), 0))
            .join(Order, Order.id == OrderLine.order_id)
            .where(OrderLine.currency == currency, OrderLine.price.is_not(None))
        )
        if since is not None:
            stmt = stmt.where(Order.created_at >= since)
        return float(self.db.execute(stmt).scalar_one() or 0)

    def _count(self, stmt: Any) -> int:
        return int(self.db.execute(stmt).scalar_one())

    def _orders_by_shop(self, since: datetime) -> dict[uuid.UUID, int]:
        rows = self.db.execute(
            select(Order.business_id, func.count())
            .where(Order.created_at >= since)
            .group_by(Order.business_id)
        ).all()
        return {row[0]: int(row[1]) for row in rows}

    def _views_by_shop(self, since: date) -> dict[uuid.UUID, int]:
        """A shop's page views plus the views of its products: a shop whose
        products are being opened is not unseen."""
        totals: dict[uuid.UUID, int] = {}
        page_views = self.db.execute(
            select(ListingViewDaily.subject_id, func.sum(ListingViewDaily.views))
            .where(
                ListingViewDaily.subject_type == ViewSubject.BUSINESS,
                ListingViewDaily.day >= since,
            )
            .group_by(ListingViewDaily.subject_id)
        ).all()
        product_views = self.db.execute(
            select(BusinessItem.business_id, func.sum(ListingViewDaily.views))
            .join(BusinessItem, BusinessItem.id == ListingViewDaily.subject_id)
            .where(
                ListingViewDaily.subject_type == ViewSubject.PRODUCT,
                ListingViewDaily.day >= since,
            )
            .group_by(BusinessItem.business_id)
        ).all()
        for shop_id, views in [*page_views, *product_views]:
            totals[shop_id] = totals.get(shop_id, 0) + int(views or 0)
        return totals

    def _views_total(self, since: date) -> int:
        return self._count(
            select(func.coalesce(func.sum(ListingViewDaily.views), 0)).where(
                ListingViewDaily.day >= since
            )
        )

    def _public_products_by_shop(self) -> dict[uuid.UUID, int]:
        visible = (
            ItemRepository(self.db)
            .public_query()
            .with_only_columns(BusinessItem.business_id, func.count(BusinessItem.id))
            .group_by(BusinessItem.business_id)
        )
        return {row[0]: int(row[1]) for row in self.db.execute(visible).all()}

    def _weekly_count(self, model: Any, week_starts: list[date]) -> list[int]:
        day = cast(model.created_at, Date)
        per_day: dict[date, Any] = {
            row[0]: row[1]
            for row in self.db.execute(
                select(day, func.count())
                .where(model.created_at >= _start_of(week_starts[0]))
                .group_by(day)
            ).all()
        }
        return _bucket(per_day, week_starts)

    def _weekly_views(self, week_starts: list[date]) -> list[int]:
        per_day: dict[date, Any] = {
            row[0]: row[1]
            for row in self.db.execute(
                select(ListingViewDaily.day, func.sum(ListingViewDaily.views))
                .where(ListingViewDaily.day >= week_starts[0])
                .group_by(ListingViewDaily.day)
            ).all()
        }
        return _bucket(per_day, week_starts)

    def _pending(self, now: datetime) -> tuple[int, int]:
        late = now - timedelta(hours=PROMISED_HOURS)
        total = waiting = 0
        for model in (Business, TalentProfile):
            total += self._count(
                select(func.count())
                .select_from(model)
                .where(model.status == BusinessStatus.PENDING_REVIEW)
            )
            waiting += self._count(
                select(func.count())
                .select_from(model)
                .where(
                    model.status == BusinessStatus.PENDING_REVIEW,
                    model.created_at < late,
                )
            )
        return total, waiting

    def _median_approval_hours(self, now: datetime) -> float | None:
        """Application to approval, for everything approved in 90 days."""
        since = now - timedelta(days=90)
        hours: list[float] = []
        for model in (Business, TalentProfile):
            for created, approved in self.db.execute(
                select(model.created_at, model.approved_at).where(
                    model.approved_at.is_not(None), model.approved_at >= since
                )
            ).all():
                hours.append(max(0.0, (approved - created).total_seconds() / 3600))
        return round(statistics.median(hours), 1) if hours else None


def _bucket(per_day: dict[date, Any], week_starts: list[date]) -> list[int]:
    totals = [0] * len(week_starts)
    for day, count in per_day.items():
        for index in range(len(week_starts) - 1, -1, -1):
            if day >= week_starts[index]:
                totals[index] += int(count or 0)
                break
    return totals


def recommend(report: GrowthReportOut) -> list[Recommendation]:
    """The next steps the numbers call for, most urgent first.

    Each rule names the lever of the value equation it moves. The wording is
    in the frontend catalog under ``growth.rec.<key>``; only the key and the
    number travel.
    """
    found: list[Recommendation] = []

    def add(key: str, lever: str, priority: str, count: int | None = None) -> None:
        found.append(
            Recommendation.model_validate(
                {"key": key, "lever": lever, "priority": priority, "count": count}
            )
        )

    orders = report.weekly.orders
    if len(orders) >= 2 and orders[-2] > 0 and orders[-1] < orders[-2]:
        add("ordersDown", "outcome", "high", orders[-2] - orders[-1])
    if report.pending_over_48h:
        add("reviewBacklog", "time", "high", report.pending_over_48h)
    if report.approved_shops and (
        report.shops_with_order_30d / report.approved_shops < PROOF_SHARE
    ):
        add("proof", "likelihood", "high", report.shops_with_order_30d)
    if report.health.unseen:
        add("unseenShops", "outcome", "high", report.health.unseen)
    if report.health.viewed_no_orders:
        add("viewsNoOrders", "likelihood", "medium", report.health.viewed_no_orders)
    if report.median_approval_hours is not None and (
        report.median_approval_hours > PROMISED_HOURS
    ):
        add("slowApproval", "time", "medium", round(report.median_approval_hours))
    if report.thin_catalogue_shops:
        add("thinCatalogue", "effort", "medium", report.thin_catalogue_shops)
    if report.approved_testimonials < TESTIMONIAL_TARGET:
        add("testimonials", "likelihood", "medium", report.approved_testimonials)
    if report.shops_without_logo:
        add("missingLogo", "effort", "low", report.shops_without_logo)
    if not found:
        add("keepGoing", "outcome", "low")
    found.sort(key=lambda rec: _PRIORITY[rec.priority])
    return found
