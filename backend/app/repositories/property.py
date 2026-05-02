from app.models.property import Property
from app.repositories.base import OrgScopedRepository


class PropertyRepository(OrgScopedRepository[Property]):
    @property
    def model_class(self) -> type[Property]:
        return Property
