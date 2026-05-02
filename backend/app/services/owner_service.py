import uuid
from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus, SourceType
from app.models.payout import Payout, PayoutStatus
from app.repositories.booking import BookingRepository
from app.repositories.payout import PayoutRepository
from app.repositories.system_config import SystemConfigRepository

OTA_SOURCES = {
    SourceType.gmail_airbnb.value,
    SourceType.gmail_mmt.value,
    SourceType.gmail_goibibo.value,
    SourceType.ical.value,
}

DEFAULT_OTA_COMMISSION_RATE = Decimal("15.0")
DEFAULT_PARTNER_COMMISSION_RATE = Decimal("10.0")
DEFAULT_OWNER_PERCENTAGE = Decimal("70.00")
DEFAULT_BREKORA_PERCENTAGE = Decimal("30.00")


class OwnerService:
    def __init__(self, session: AsyncSession, org_id: uuid.UUID):
        self.session = session
        self.org_id = org_id
        self.system_config_repo = SystemConfigRepository(session, org_id)
        self.booking_repo = BookingRepository(session, org_id)
        self.payout_repo = PayoutRepository(session, org_id)

    async def _get_decimal_config(self, key: str, default: Decimal) -> Decimal:
        config = await self.system_config_repo.get_by_key(key)
        if config is not None:
            try:
                return Decimal(config.value)
            except Exception:
                pass
        return default

    async def calculate_pnl(self, property_id: uuid.UUID, month: date) -> dict:
        month_start = date(month.year, month.month, 1)
        _, last_day = monthrange(month.year, month.month)
        month_end = date(month.year, month.month, last_day)

        stmt = (
            select(Booking)
            .where(Booking.org_id == self.org_id)
            .where(Booking.property_id == property_id)
            .where(Booking.status == BookingStatus.confirmed.value)
            .where(Booking.check_in >= month_start)
            .where(Booking.check_in <= month_end)
        )
        result = await self.session.execute(stmt)
        bookings = result.scalars().all()

        ota_rate = await self._get_decimal_config("ota_commission_rate", DEFAULT_OTA_COMMISSION_RATE)
        partner_rate = await self._get_decimal_config("partner_commission_rate", DEFAULT_PARTNER_COMMISSION_RATE)

        gross_amount = Decimal("0.00")
        ota_commission = Decimal("0.00")
        partner_commission = Decimal("0.00")
        gst_amount = Decimal("0.00")

        booking_breakdown = []

        for booking in bookings:
            gross = booking.gross_amount.quantize(Decimal("0.01"))
            gross_amount += gross
            gst_amount += booking.tax_amount.quantize(Decimal("0.01"))

            booking_ota_commission = Decimal("0.00")
            booking_partner_commission = Decimal("0.00")

            if booking.source_type in OTA_SOURCES:
                booking_ota_commission = (gross * ota_rate / Decimal("100")).quantize(Decimal("0.01"))
                ota_commission += booking_ota_commission

            if booking.partner_attribution_id:
                booking_partner_commission = (gross * partner_rate / Decimal("100")).quantize(Decimal("0.01"))
                partner_commission += booking_partner_commission

            net_for_booking = gross - booking_ota_commission - booking_partner_commission
            booking_breakdown.append({
                "booking_id": str(booking.id),
                "source": booking.source_type,
                "gross": gross,
                "ota_commission": booking_ota_commission,
                "partner_commission": booking_partner_commission,
                "net": net_for_booking,
            })

        net_distributable = gross_amount - ota_commission - partner_commission

        return {
            "property_id": str(property_id),
            "month": month.strftime("%Y-%m"),
            "gross_amount": gross_amount.quantize(Decimal("0.01")),
            "ota_commission": ota_commission.quantize(Decimal("0.01")),
            "partner_commission": partner_commission.quantize(Decimal("0.01")),
            "gst_amount": gst_amount.quantize(Decimal("0.01")),
            "net_distributable": net_distributable.quantize(Decimal("0.01")),
            "booking_count": len(bookings),
            "booking_breakdown": booking_breakdown,
        }

    async def calculate_payout(self, property_id: uuid.UUID, month: date) -> Payout:
        pnl = await self.calculate_pnl(property_id, month)
        month_str = month.strftime("%Y-%m")

        # Determine split
        owner_pct = await self._get_decimal_config(
            f"owner_split_{property_id}",
            await self._get_decimal_config("default_owner_split", DEFAULT_OWNER_PERCENTAGE),
        )
        brekora_pct = await self._get_decimal_config(
            f"brekora_split_{property_id}",
            await self._get_decimal_config("default_brekora_split", DEFAULT_BREKORA_PERCENTAGE),
        )

        # If only owner_split is configured, derive brekora from it
        if owner_pct + brekora_pct != Decimal("100.00"):
            brekora_pct = Decimal("100.00") - owner_pct

        net_distributable = pnl["net_distributable"]
        owner_share = (net_distributable * owner_pct / Decimal("100")).quantize(Decimal("0.01"))
        brekora_share = (net_distributable * brekora_pct / Decimal("100")).quantize(Decimal("0.01"))

        # Idempotent create/update
        existing = await self.payout_repo.get_by_property_and_month(property_id, month_str)
        if existing is not None:
            payout = await self.payout_repo.update(existing, {
                "gross_amount": pnl["gross_amount"],
                "ota_commission": pnl["ota_commission"],
                "partner_commission": pnl["partner_commission"],
                "gst_amount": pnl["gst_amount"],
                "net_distributable": net_distributable,
                "owner_share": owner_share,
                "brekora_share": brekora_share,
                "owner_percentage": owner_pct.quantize(Decimal("0.01")),
                "brekora_percentage": brekora_pct.quantize(Decimal("0.01")),
            })
        else:
            payout = await self.payout_repo.create({
                "property_id": property_id,
                "month": month_str,
                "gross_amount": pnl["gross_amount"],
                "ota_commission": pnl["ota_commission"],
                "partner_commission": pnl["partner_commission"],
                "gst_amount": pnl["gst_amount"],
                "net_distributable": net_distributable,
                "owner_share": owner_share,
                "brekora_share": brekora_share,
                "owner_percentage": owner_pct.quantize(Decimal("0.01")),
                "brekora_percentage": brekora_pct.quantize(Decimal("0.01")),
                "status": PayoutStatus.pending,
            })

        return payout

    async def generate_monthly_statement(self, property_id: uuid.UUID, month: date) -> dict:
        payout = await self.calculate_payout(property_id, month)
        pnl = await self.calculate_pnl(property_id, month)

        return {
            "property_id": str(property_id),
            "month": month.strftime("%Y-%m"),
            "summary": {
                "gross_amount": float(payout.gross_amount),
                "ota_commission": float(payout.ota_commission),
                "partner_commission": float(payout.partner_commission),
                "gst_amount": float(payout.gst_amount),
                "net_distributable": float(payout.net_distributable),
                "owner_share": float(payout.owner_share),
                "brekora_share": float(payout.brekora_share),
                "owner_percentage": float(payout.owner_percentage),
                "brekora_percentage": float(payout.brekora_percentage),
                "status": payout.status,
            },
            "chart": {
                "labels": ["Owner Share", "Brekora Share", "OTA Commission", "Partner Commission", "GST"],
                "values": [
                    float(payout.owner_share),
                    float(payout.brekora_share),
                    float(payout.ota_commission),
                    float(payout.partner_commission),
                    float(payout.gst_amount),
                ],
            },
            "bookings": pnl["booking_breakdown"],
        }
