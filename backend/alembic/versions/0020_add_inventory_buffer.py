"""add inventory_buffer table"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0020"
down_revision: Union[str, None, Sequence[str]] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inventory_buffer",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("property_id", UUID(as_uuid=True), sa.ForeignKey("property.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("room_type_id", UUID(as_uuid=True), sa.ForeignKey("room_type.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("buffer_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("org_id", "property_id", "room_type_id", "date", name="uq_buffer_org_room_date"),
    )


def downgrade() -> None:
    op.drop_table("inventory_buffer")
