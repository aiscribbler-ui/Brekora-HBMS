from app.models.raw_email import RawEmail
from app.repositories.base import OrgScopedRepository


class RawEmailRepository(OrgScopedRepository[RawEmail]):
    @property
    def model_class(self) -> type[RawEmail]:
        return RawEmail
