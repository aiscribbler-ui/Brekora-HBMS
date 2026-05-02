"""add payout table"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0026"
down_revision: Union[str, None, Sequence[str]] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payout",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("property_id", UUID(as_uuid=True), sa.ForeignKey("property.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("month", sa.String(7), nullable=False, index=True),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("ota_commission", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("partner_commission", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("gst_amount", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("net_distributable", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("owner_share", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("brekora_share", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("owner_percentage", sa.Numeric(5, 2), nullable=False, server_default=sa.text("70.00")),
        sa.Column("brekora_percentage", sa.Numeric(5, 2), nullable=False, server_default=sa.text("30.00")),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("property_id", "month", name="uq_payout_property_month"),
    )


def downgrade() -> None:
    op.drop_table("payout")
