import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.system_config import SystemConfigRepository


DEFAULT_GST_RATE = Decimal("0.12")


class GSTService:
    """Dedicated GST calculation service with admin-configurable rates."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_gst_rate(
        self, property_id: uuid.UUID | None = None, org_id: uuid.UUID | None = None
    ) -> Decimal:
        """Return GST rate for the given scope.

        For MVP: falls back to default 12% if no org-specific config exists.
        Future: property-specific overrides via property_id.
        """
        if org_id is None:
            settings = get_settings()
            org_id = settings.DEFAULT_ORG_ID

        repo = SystemConfigRepository(self.session, org_id)
        config = await repo.get_by_key("gst_rate")
        if config is not None:
            try:
                return Decimal(config.value)
            except Exception:
                pass
        return DEFAULT_GST_RATE

    async def calculate(
        self,
        subtotal: Decimal,
        discount: Decimal,
        property_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
    ) -> dict[str, Decimal]:
        """Calculate GST breakdown from subtotal and discount."""
        rate = await self.get_gst_rate(property_id=property_id, org_id=org_id)
        taxable_value = (subtotal - discount).quantize(Decimal("0.01"))
        if taxable_value < 0:
            taxable_value = Decimal("0.00")
        gst_amount = (taxable_value * rate).quantize(Decimal("0.01"))
        total = (taxable_value + gst_amount).quantize(Decimal("0.01"))
        return {
            "taxable_value": taxable_value,
            "gst_amount": gst_amount,
            "total": total,
            "rate": rate,
        }

    @staticmethod
    def reverse_calculate(gross_amount: Decimal, rate: Decimal) -> dict[str, Decimal]:
        """Reverse-calculate taxable value and GST from a gross (tax-inclusive) amount."""
        taxable_value = (gross_amount / (1 + rate)).quantize(Decimal("0.01"))
        gst_amount = (gross_amount - taxable_value).quantize(Decimal("0.01"))
        return {
            "taxable_value": taxable_value,
            "gst_amount": gst_amount,
            "total": gross_amount.quantize(Decimal("0.01")),
            "rate": rate,
        }
