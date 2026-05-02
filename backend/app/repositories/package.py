import uuid

from sqlalchemy import select

from app.models.package import Package, PackageAddOn, PackageComposition
from app.repositories.base import OrgScopedRepository


class PackageRepository(OrgScopedRepository[Package]):
    @property
    def model_class(self) -> type[Package]:
        return Package

    async def get_multi_by_property(
        self, property_id: uuid.UUID, *, skip: int = 0, limit: int = 100
    ) -> list[Package]:
        stmt = (
            select(Package)
            .where(Package.property_id == property_id)
            .offset(skip)
            .limit(limit)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class PackageCompositionRepository(OrgScopedRepository[PackageComposition]):
    @property
    def model_class(self) -> type[PackageComposition]:
        return PackageComposition

    async def get_multi_by_package(
        self, package_id: uuid.UUID, *, skip: int = 0, limit: int = 100
    ) -> list[PackageComposition]:
        stmt = (
            select(PackageComposition)
            .where(PackageComposition.package_id == package_id)
            .offset(skip)
            .limit(limit)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class PackageAddOnRepository(OrgScopedRepository[PackageAddOn]):
    @property
    def model_class(self) -> type[PackageAddOn]:
        return PackageAddOn

    async def get_multi_by_package(
        self, package_id: uuid.UUID, *, skip: int = 0, limit: int = 100
    ) -> list[PackageAddOn]:
        stmt = (
            select(PackageAddOn)
            .where(PackageAddOn.package_id == package_id)
            .offset(skip)
            .limit(limit)
        )
        stmt = self._apply_org_scope(stmt)
        result = await self.session.execute(stmt)
        return result.scalars().all()
