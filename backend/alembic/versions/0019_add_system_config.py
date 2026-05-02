"""add system_config table"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0019"
down_revision: Union[str, None, Sequence[str]] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_config",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("data_type", sa.String(20), nullable=False, server_default="string"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("org_id", "key", name="uq_system_config_org_key"),
    )

    # Seed default GST rate for the default organization
    op.execute(
        """
        INSERT INTO system_config (org_id, key, value, data_type)
        VALUES ('00000000-0000-0000-0000-000000000001', 'gst_rate', '0.12', 'number')
        ON CONFLICT (org_id, key) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("system_config")
