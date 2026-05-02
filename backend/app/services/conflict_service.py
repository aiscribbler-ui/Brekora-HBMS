import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.package import Package, PackageComposition
from app.models.room_type import RoomType
from app.services.availability_service import AvailabilityService
from app.services.pricing_service import PricingService


class ConflictService:
    """Find alternative room types and packages when a booking fails
    due to inventory unavailability.
    """

    def __init__(self, session: AsyncSession, org_id: uuid.UUID):
        self.session = session
        self.org_id = org_id
        self.availability_service = AvailabilityService(session)
        self.pricing_service = PricingService(session)

    async def find_alternatives(
        self,
        property_id: uuid.UUID,
        check_in: date,
        check_out: date,
        guests: int,
        excluded_room_type_id: uuid.UUID | None = None,
        excluded_package_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Return up to 5 available alternatives sorted by price (cheapest first).

        Each alternative dict has keys:
        - item_type: "room" or "package"
        - item_id: uuid.UUID
        - item_name: str
        - available_count: int
        - suggested_price: Decimal
        - currency: str
        """
        alternatives: list[dict] = []

        # --- Room types ---
        rt_stmt = (
            select(RoomType)
            .where(
                RoomType.property_id == property_id,
                RoomType.org_id == self.org_id,
                RoomType.is_active.is_(True),
                RoomType.is_archived.is_(False),
                RoomType.base_capacity >= guests,
            )
        )
        rt_result = await self.session.execute(rt_stmt)
        room_types = rt_result.scalars().all()

        for rt in room_types:
            if excluded_room_type_id is not None and rt.id == excluded_room_type_id:
                continue

            avail = await self.availability_service.get_room_availability(
                property_id=property_id,
                room_type_id=rt.id,
                check_in=check_in,
                check_out=check_out,
                org_id=self.org_id,
            )
            if not avail:
                continue
            min_available = min(night["available_count"] for night in avail)
            if min_available < 1:
                continue

            price = await self.pricing_service.calculate_room_price(
                room_type_id=rt.id,
                check_in=check_in,
                check_out=check_out,
                guests=guests,
                channel_source="direct",
            )

            alternatives.append(
                {
                    "item_type": "room",
                    "item_id": rt.id,
                    "item_name": rt.name,
                    "available_count": min_available,
                    "suggested_price": price.total_amount,
                    "currency": price.currency,
                }
            )

        # --- Packages ---
        pkg_stmt = (
            select(Package)
            .where(
                Package.property_id == property_id,
                Package.org_id == self.org_id,
                Package.is_active.is_(True),
                Package.is_archived.is_(False),
                Package.status == "active",
            )
        )
        pkg_result = await self.session.execute(pkg_stmt)
        packages = pkg_result.scalars().all()

        for pkg in packages:
            if excluded_package_id is not None and pkg.id == excluded_package_id:
                continue

            # occupancy filter
            if pkg.max_occupancy is not None and guests > pkg.max_occupancy:
                continue

            comp_stmt = (
                select(PackageComposition)
                .where(
                    PackageComposition.package_id == pkg.id,
                    PackageComposition.org_id == self.org_id,
                )
            )
            comp_result = await self.session.execute(comp_stmt)
            compositions = comp_result.scalars().all()

            package_available = True
            min_available = None
            for comp in compositions:
                comp_avail = await self.availability_service.get_room_availability(
                    property_id=property_id,
                    room_type_id=comp.room_type_id,
                    check_in=check_in,
                    check_out=check_out,
                    org_id=self.org_id,
                )
                if not comp_avail:
                    package_available = False
                    break
                comp_min = min(night["available_count"] for night in comp_avail)
                if comp_min < comp.quantity:
                    package_available = False
                    break
                if min_available is None or comp_min < min_available:
                    min_available = comp_min

            if not package_available or min_available is None:
                continue

            price = await self.pricing_service.calculate_package_price(
                package_id=pkg.id,
                check_in=check_in,
                check_out=check_out,
                guests=guests,
                channel_source="direct",
            )

            alternatives.append(
                {
                    "item_type": "package",
                    "item_id": pkg.id,
                    "item_name": pkg.name,
                    "available_count": min_available,
                    "suggested_price": price.total_amount,
                    "currency": price.currency,
                }
            )

        # Sort by total price ascending and keep top 5
        alternatives.sort(key=lambda alt: alt["suggested_price"])
        return alternatives[:5]
