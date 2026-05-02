"""add ota_settings table"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0016"
down_revision: Union[str, None, Sequence[str]] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ota_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ota_source", sa.String(50), nullable=False),
        sa.Column("auto_confirm", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("min_confidence", sa.Float, nullable=False, server_default=sa.text("0.95")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("org_id", "ota_source", name="uq_ota_settings_org_source"),
    )


def downgrade() -> None:
    op.drop_table("ota_settings")
