"""add property and room_type

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "property",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("gstin", sa.String(length=50), nullable=True),
        sa.Column("pan", sa.String(length=50), nullable=True),
        sa.Column("owner_contact", sa.String(length=255), nullable=True),
        sa.Column("photos", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("amenities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("default_check_in_time", sa.Time(), nullable=True),
        sa.Column("default_check_out_time", sa.Time(), nullable=True),
        sa.Column("cancellation_policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.ForeignKeyConstraint(["org_id"], ["organization.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_property_org_id", "property", ["org_id"], unique=False)

    op.create_table(
        "room_type",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("base_capacity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("max_capacity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "default_rate", sa.Numeric(precision=12, scale=2), nullable=False, server_default=sa.text("0.00")
        ),
        sa.Column("min_stay", sa.Integer(), nullable=True),
        sa.Column("max_stay", sa.Integer(), nullable=True),
        sa.Column("photos", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.ForeignKeyConstraint(["org_id"], ["organization.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["property.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_room_type_org_id", "room_type", ["org_id"], unique=False)
    op.create_index("ix_room_type_property_id", "room_type", ["property_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_room_type_property_id", table_name="room_type")
    op.drop_index("ix_room_type_org_id", table_name="room_type")
    op.drop_table("room_type")
    op.drop_index("ix_property_org_id", table_name="property")
    op.drop_table("property")
