from app.models.cancellation_policy import CancellationPolicy
from app.repositories.base import OrgScopedRepository


class CancellationPolicyRepository(OrgScopedRepository[CancellationPolicy]):
    @property
    def model_class(self) -> type[CancellationPolicy]:
        return CancellationPolicy
