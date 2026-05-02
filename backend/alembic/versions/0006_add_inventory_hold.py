"""add inventory_hold

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inventory_hold",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dates", sa.ARRAY(sa.Date()), nullable=False),
        sa.Column(
            "add_on_holds",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organization.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["property.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["room_type_id"],
            ["room_type.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_inventory_hold_booking_id",
        "inventory_hold",
        ["booking_id"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_hold_property_id",
        "inventory_hold",
        ["property_id"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_hold_room_type_id",
        "inventory_hold",
        ["room_type_id"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_hold_expires_at",
        "inventory_hold",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_hold_status",
        "inventory_hold",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_hold_org_id",
        "inventory_hold",
        ["org_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_hold_org_id", table_name="inventory_hold")
    op.drop_index("ix_inventory_hold_status", table_name="inventory_hold")
    op.drop_index("ix_inventory_hold_expires_at", table_name="inventory_hold")
    op.drop_index("ix_inventory_hold_room_type_id", table_name="inventory_hold")
    op.drop_index("ix_inventory_hold_property_id", table_name="inventory_hold")
    op.drop_index("ix_inventory_hold_booking_id", table_name="inventory_hold")
    op.drop_table("inventory_hold")
