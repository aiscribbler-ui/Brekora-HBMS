import hashlib
import json
import uuid
from datetime import date

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.package import Package, PackageComposition
from app.models.property import Property
from app.models.room_type import RoomType
from app.schemas.pricing import PriceBreakdown as PriceBreakdownSchema
from app.schemas.search import PropertySnippet, SearchRequest, SearchResponse, SearchResultItem
from app.services.availability_service import AvailabilityService
from app.services.pricing_service import PricingService, PriceBreakdown as PriceBreakdownDataclass


class SearchService:
    """Public search engine for room types and packages with live pricing."""

    def __init__(self, session: AsyncSession, redis: Redis | None = None):
        self.session = session
        self.redis = redis
        self.availability_service = AvailabilityService(session, redis)
        self.pricing_service = PricingService(session)

    @staticmethod
    def _cache_key(org_id: uuid.UUID, search_request: SearchRequest) -> str:
        payload = {
            "location": search_request.location,
            "check_in": search_request.check_in.isoformat(),
            "check_out": search_request.check_out.isoformat(),
            "guests": search_request.guests,
            "promo_code": search_request.promo_code,
        }
        hash_val = hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return f"search:{org_id}:{hash_val}"

    @staticmethod
    def _price_breakdown_to_schema(
        price: PriceBreakdownDataclass,
    ) -> PriceBreakdownSchema:
        return PriceBreakdownSchema(
            subtotal=price.subtotal,
            discount_amount=price.discount_amount,
            taxable_amount=price.taxable_amount,
            tax_amount=price.tax_amount,
            channel_markup_amount=price.channel_markup_amount,
            total_amount=price.total_amount,
            currency=price.currency,
            breakdown_per_night=price.breakdown_per_night,
        )

    async def search(
        self,
        search_request: SearchRequest,
        org_id: uuid.UUID,
    ) -> SearchResponse:
        if search_request.check_in >= search_request.check_out:
            raise ValueError("check_out must be after check_in")

        cache_key = self._cache_key(org_id, search_request)

        if self.redis is not None:
            cached = await self.redis.get(cache_key)
            if cached:
                return SearchResponse.model_validate_json(cached)

        location_pattern = f"%{search_request.location}%"
        prop_stmt = (
            select(Property)
            .where(
                Property.org_id == org_id,
                Property.is_active.is_(True),
                Property.is_archived.is_(False),
            )
            .where(
                (Property.address.ilike(location_pattern))
                | (Property.name.ilike(location_pattern))
            )
        )
        result = await self.session.execute(prop_stmt)
        properties = result.scalars().all()

        results: list[SearchResultItem] = []

        for prop in properties:
            prop_snippet = PropertySnippet(
                id=prop.id,
                name=prop.name,
                address=prop.address,
                photos=prop.photos,
                amenities=prop.amenities,
            )

            # Active room types
            rt_stmt = (
                select(RoomType)
                .where(
                    RoomType.property_id == prop.id,
                    RoomType.is_active.is_(True),
                    RoomType.is_archived.is_(False),
                )
            )
            rt_result = await self.session.execute(rt_stmt)
            room_types = rt_result.scalars().all()

            for rt in room_types:
                avail = await self.availability_service.get_room_availability(
                    property_id=prop.id,
                    room_type_id=rt.id,
                    check_in=search_request.check_in,
                    check_out=search_request.check_out,
                    org_id=org_id,
                )
                if not avail:
                    continue
                if any(night["available_count"] <= 0 for night in avail):
                    continue

                price = await self.pricing_service.calculate_room_price(
                    room_type_id=rt.id,
                    check_in=search_request.check_in,
                    check_out=search_request.check_out,
                    guests=search_request.guests,
                    promo_code=search_request.promo_code,
                    channel_source="direct",
                )

                results.append(
                    SearchResultItem(
                        type="room",
                        id=rt.id,
                        name=rt.name,
                        photos=rt.photos,
                        description=rt.description,
                        available=True,
                        price_breakdown=self._price_breakdown_to_schema(price),
                        property=prop_snippet,
                    )
                )

            # Active packages
            pkg_stmt = (
                select(Package)
                .where(
                    Package.property_id == prop.id,
                    Package.is_active.is_(True),
                    Package.is_archived.is_(False),
                    Package.status == "active",
                )
            )
            pkg_result = await self.session.execute(pkg_stmt)
            packages = pkg_result.scalars().all()

            for pkg in packages:
                comp_stmt = (
                    select(PackageComposition)
                    .where(
                        PackageComposition.package_id == pkg.id,
                        PackageComposition.org_id == org_id,
                    )
                )
                comp_result = await self.session.execute(comp_stmt)
                compositions = comp_result.scalars().all()

                package_available = True
                for comp in compositions:
                    comp_avail = await self.availability_service.get_room_availability(
                        property_id=prop.id,
                        room_type_id=comp.room_type_id,
                        check_in=search_request.check_in,
                        check_out=search_request.check_out,
                        org_id=org_id,
                    )
                    if not comp_avail:
                        package_available = False
                        break
                    if any(
                        night["available_count"] < comp.quantity
                        for night in comp_avail
                    ):
                        package_available = False
                        break

                if not package_available:
                    continue

                price = await self.pricing_service.calculate_package_price(
                    package_id=pkg.id,
                    check_in=search_request.check_in,
                    check_out=search_request.check_out,
                    guests=search_request.guests,
                    promo_code=search_request.promo_code,
                    channel_source="direct",
                )

                results.append(
                    SearchResultItem(
                        type="package",
                        id=pkg.id,
                        name=pkg.name,
                        photos=None,
                        description=pkg.description,
                        available=True,
                        price_breakdown=self._price_breakdown_to_schema(price),
                        property=prop_snippet,
                    )
                )

        response = SearchResponse(results=results)

        if self.redis is not None:
            await self.redis.setex(cache_key, 60, response.model_dump_json())

        return response
