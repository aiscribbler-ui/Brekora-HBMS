from app.models.organization import Organization
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    @property
    def model_class(self) -> type[Organization]:
        return Organization
