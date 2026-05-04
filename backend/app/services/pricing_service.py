import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.package import Package
from app.models.promo_code import PromoCode
from app.models.rate_plan import RatePlan
from app.models.room_type import RoomType
from app.models.seasonal_calendar import SeasonalCalendar
from app.repositories.pricing import PromoCodeRepository, RatePlanRepository, SeasonalCalendarRepository


from app.services.gst_service import GSTService


@dataclass
class PriceBreakdown:
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    gst_rate: Decimal = Decimal("0.12")
    channel_markup_amount: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")
    currency: str = "INR"
    breakdown_per_night: list[dict[str, Any]] = field(default_factory=list)


class PricingService:
    """Calculate prices for rooms and packages with rate plans, seasonal
    multipliers, promo codes, and channel markup.
    """

    GST_RATE: Decimal = Decimal("0.12")
    CHANNEL_MARKUP_RATE: Decimal = Decimal("0.18")

    def __init__(self, session: AsyncSession):
        self.session = session
        # Dummy org_id; real org_id is passed per-query to repository methods
        dummy_org = uuid.UUID("00000000-0000-0000-0000-000000000000")
        self.rate_plan_repo = RatePlanRepository(session, dummy_org)
        self.seasonal_repo = SeasonalCalendarRepository(session, dummy_org)
        self.promo_repo = PromoCodeRepository(session, dummy_org)

    @staticmethod
    def _nights_between(check_in: date, check_out: date) -> int:
        return (check_out - check_in).days

    @staticmethod
    def _date_range(check_in: date, check_out: date) -> list[date]:
        return [
            check_in + timedelta(days=i)
            for i in range((check_out - check_in).days)
        ]

    @staticmethod
    def _apply_discount(amount: Decimal, discount_type: str, discount_value: Decimal) -> Decimal:
        if discount_type == "percentage":
            return (amount * discount_value / Decimal("100")).quantize(Decimal("0.01"))
        elif discount_type == "fixed":
            return min(amount, discount_value)
        return Decimal("0.00")

    def _calculate_channel_markup(
        self, taxable_amount: Decimal, tax_amount: Decimal, is_ota: bool
    ) -> Decimal:
        if not is_ota:
            return Decimal("0.00")
        base = taxable_amount + tax_amount
        return (base * self.CHANNEL_MARKUP_RATE).quantize(Decimal("0.01"))

    async def _get_seasonal_multipliers(
        self, org_id: uuid.UUID, check_in: date, check_out: date
    ) -> dict[date, Decimal]:
        """Return the highest seasonal multiplier for each night."""
        seasons = await self.seasonal_repo.get_active_for_date_range(check_in, check_out, org_id=org_id)

        multipliers: dict[date, Decimal] = {}
        for night in self._date_range(check_in, check_out):
            applicable = [
                s.multiplier
                for s in seasons
                if s.start_date <= night <= s.end_date
            ]
            multipliers[night] = max(applicable) if applicable else Decimal("1.00")
        return multipliers

    async def _validate_promo_code(
        self,
        org_id: uuid.UUID,
        code: str | None,
        booking_type: str,
        check_in: date,
    ) -> PromoCode | None:
        if not code:
            return None
        promo = await self.promo_repo.get_by_code(code, org_id=org_id)
        if not promo:
            return None
        if not promo.is_active:
            return None
        if promo.max_uses is not None and promo.used_count >= promo.max_uses:
            return None
        if promo.valid_from and check_in < promo.valid_from:
            return None
        if promo.valid_to and check_in > promo.valid_to:
            return None
        if promo.applicable_booking_types and booking_type not in promo.applicable_booking_types:
            return None
        return promo

    async def _get_rate_plan(
        self, org_id: uuid.UUID, code: str | None
    ) -> RatePlan | None:
        if not code:
            return None
        rp = await self.rate_plan_repo.get_by_code(code, org_id=org_id)
        if not rp or not rp.is_active:
            return None
        return rp

    async def calculate_room_price(
        self,
        room_type_id: uuid.UUID,
        check_in: date,
        check_out: date,
        rate_plan_code: str | None = None,
        guests: int | None = None,
        promo_code: str | None = None,
        channel_source: str | None = None,
    ) -> PriceBreakdown:
        from sqlalchemy import select

        stmt = select(RoomType).where(
            RoomType.id == room_type_id,
            RoomType.is_active.is_(True),
            RoomType.is_archived.is_(False),
        )
        result = await self.session.execute(stmt)
        room_type = result.scalar_one_or_none()
        if room_type is None:
            raise ValueError("Room type not found")

        org_id = room_type.org_id
        nights = self._nights_between(check_in, check_out)
        if nights <= 0:
            raise ValueError("check_out must be after check_in")

        multipliers = await self._get_seasonal_multipliers(org_id, check_in, check_out)
        rate_plan = await self._get_rate_plan(org_id, rate_plan_code)

        # Validate rate plan night constraints
        if rate_plan is not None:
            if rate_plan.min_nights is not None and nights < rate_plan.min_nights:
                rate_plan = None
            if rate_plan is not None and rate_plan.max_nights is not None and nights > rate_plan.max_nights:
                rate_plan = None

        promo = await self._validate_promo_code(org_id, promo_code, "room", check_in)

        breakdown_per_night: list[dict[str, Any]] = []
        subtotal = Decimal("0.00")
        rate_plan_discount = Decimal("0.00")

        for night in self._date_range(check_in, check_out):
            base_rate = room_type.default_rate
            multiplier = multipliers.get(night, Decimal("1.00"))

            # Apply rate plan discount to base rate
            night_rate = base_rate
            night_rp_discount = Decimal("0.00")
            if rate_plan is not None:
                night_rp_discount = self._apply_discount(
                    night_rate, rate_plan.discount_type, rate_plan.discount_value
                )
                night_rate -= night_rp_discount
                rate_plan_discount += night_rp_discount

            # Apply seasonal multiplier
            night_rate = (night_rate * multiplier).quantize(Decimal("0.01"))

            subtotal += night_rate
            breakdown_per_night.append(
                {
                    "date": night.isoformat(),
                    "base_rate": str(base_rate),
                    "multiplier": str(multiplier),
                    "rate_plan_discount": str(night_rp_discount),
                    "night_total": str(night_rate),
                }
            )

        # Apply promo code discount to subtotal after rate plan
        promo_discount = Decimal("0.00")
        if promo is not None:
            promo_discount = self._apply_discount(
                subtotal, promo.discount_type, promo.discount_value
            )

        discount_amount = (rate_plan_discount + promo_discount).quantize(Decimal("0.01"))
        taxable_amount = (subtotal - promo_discount).quantize(Decimal("0.01"))
        if taxable_amount < 0:
            taxable_amount = Decimal("0.00")

        gst_result = await GSTService(self.session).calculate(
            subtotal=subtotal.quantize(Decimal("0.01")),
            discount=promo_discount,
            org_id=org_id,
        )
        tax_amount = gst_result["gst_amount"]
        gst_rate = gst_result["rate"]
        is_ota = channel_source is not None and channel_source not in ("direct", "manual")
        channel_markup = self._calculate_channel_markup(taxable_amount, tax_amount, is_ota)
        total_amount = (taxable_amount + tax_amount + channel_markup).quantize(Decimal("0.01"))

        return PriceBreakdown(
            subtotal=subtotal.quantize(Decimal("0.01")),
            discount_amount=discount_amount,
            taxable_amount=taxable_amount,
            tax_amount=tax_amount,
            gst_rate=gst_rate,
            channel_markup_amount=channel_markup,
            total_amount=total_amount,
            currency="INR",
            breakdown_per_night=breakdown_per_night,
        )

    async def calculate_package_price(
        self,
        package_id: uuid.UUID,
        check_in: date,
        check_out: date,
        guests: int | None = None,
        promo_code: str | None = None,
        channel_source: str | None = None,
    ) -> PriceBreakdown:
        from sqlalchemy import select

        stmt = select(Package).where(
            Package.id == package_id,
            Package.is_active.is_(True),
            Package.is_archived.is_(False),
        )
        result = await self.session.execute(stmt)
        package = result.scalar_one_or_none()
        if package is None:
            raise ValueError("Package not found")

        org_id = package.org_id
        nights = self._nights_between(check_in, check_out)
        if nights <= 0:
            raise ValueError("check_out must be after check_in")

        multipliers = await self._get_seasonal_multipliers(org_id, check_in, check_out)
        promo = await self._validate_promo_code(org_id, promo_code, "package", check_in)

        # Determine base price and apply dynamic pricing rules
        base_price = package.base_price
        dynamic_rules = package.dynamic_pricing_rules or {}

        # Occupancy scaling
        if guests and "occupancy_scaling" in dynamic_rules:
            occ = dynamic_rules["occupancy_scaling"]
            base_occ = occ.get("base_occupancy", package.max_occupancy or 2)
            extra_charge = Decimal(str(occ.get("extra_guest_charge", 0)))
            if guests > base_occ:
                # Apply per extra guest per night
                base_price += extra_charge * (guests - base_occ) * nights

        # Early-bird discount
        early_bird_discount = Decimal("0.00")
        if "early_bird" in dynamic_rules:
            eb = dynamic_rules["early_bird"]
            min_days = eb.get("min_days_before", 0)
            days_before = (check_in - date.today()).days
            if days_before >= min_days:
                disc_val = Decimal(str(eb.get("discount_percentage", 0)))
                early_bird_discount = self._apply_discount(base_price, "percentage", disc_val)

        # Group discount
        group_discount = Decimal("0.00")
        if guests and "group_discount" in dynamic_rules:
            gd = dynamic_rules["group_discount"]
            min_guests = gd.get("min_guests", 0)
            if guests >= min_guests:
                disc_val = Decimal(str(gd.get("discount_percentage", 0)))
                group_discount = self._apply_discount(base_price, "percentage", disc_val)

        # Apply highest of early_bird or group discount
        dynamic_discount = max(early_bird_discount, group_discount)
        price_after_dynamic = base_price - dynamic_discount

        # Seasonal multiplier applied as average across nights
        avg_multiplier = Decimal("1.00")
        if multipliers:
            avg_multiplier = (
                sum(multipliers.values()) / len(multipliers)
            ).quantize(Decimal("0.01"))

        subtotal = (price_after_dynamic * avg_multiplier).quantize(Decimal("0.01"))

        # Apply promo code
        promo_discount = Decimal("0.00")
        if promo is not None:
            promo_discount = self._apply_discount(
                subtotal, promo.discount_type, promo.discount_value
            )

        discount_amount = (dynamic_discount + promo_discount).quantize(Decimal("0.01"))
        taxable_amount = (subtotal - promo_discount).quantize(Decimal("0.01"))
        if taxable_amount < 0:
            taxable_amount = Decimal("0.00")

        gst_result = await GSTService(self.session).calculate(
            subtotal=subtotal.quantize(Decimal("0.01")),
            discount=promo_discount,
            org_id=org_id,
        )
        tax_amount = gst_result["gst_amount"]
        gst_rate = gst_result["rate"]
        is_ota = channel_source is not None and channel_source not in ("direct", "manual")
        channel_markup = self._calculate_channel_markup(taxable_amount, tax_amount, is_ota)
        total_amount = (taxable_amount + tax_amount + channel_markup).quantize(Decimal("0.01"))

        breakdown_per_night: list[dict[str, Any]] = []
        nightly_base = subtotal / nights if nights > 0 else Decimal("0.00")
        for night in self._date_range(check_in, check_out):
            multiplier = multipliers.get(night, Decimal("1.00"))
            breakdown_per_night.append(
                {
                    "date": night.isoformat(),
                    "base_price": str(base_price),
                    "dynamic_discount": str(dynamic_discount),
                    "multiplier": str(multiplier),
                    "night_total": str(nightly_base.quantize(Decimal("0.01"))),
                }
            )

        return PriceBreakdown(
            subtotal=subtotal.quantize(Decimal("0.01")),
            discount_amount=discount_amount,
            taxable_amount=taxable_amount,
            tax_amount=tax_amount,
            gst_rate=gst_rate,
            channel_markup_amount=channel_markup,
            total_amount=total_amount,
            currency="INR",
            breakdown_per_night=breakdown_per_night,
        )
