"""add ota_mapping

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ota_mapping",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ota_source", sa.String(length=50), nullable=False),
        sa.Column("listing_id", sa.String(length=255), nullable=False),
        sa.Column("room_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")
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
        sa.UniqueConstraint(
            "org_id", "ota_source", "listing_id",
            name="uq_ota_mapping_org_source_listing",
        ),
    )
    op.create_index(
        "ix_ota_mapping_org_id", "ota_mapping", ["org_id"], unique=False
    )
    op.create_index(
        "ix_ota_mapping_property_id", "ota_mapping", ["property_id"], unique=False
    )
    op.create_index(
        "ix_ota_mapping_room_type_id", "ota_mapping", ["room_type_id"], unique=False
    )
    op.create_index(
        "ix_ota_mapping_ota_source", "ota_mapping", ["ota_source"], unique=False
    )
    op.create_index(
        "ix_ota_mapping_listing_id", "ota_mapping", ["listing_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_ota_mapping_listing_id", table_name="ota_mapping")
    op.drop_index("ix_ota_mapping_ota_source", table_name="ota_mapping")
    op.drop_index("ix_ota_mapping_room_type_id", table_name="ota_mapping")
    op.drop_index("ix_ota_mapping_property_id", table_name="ota_mapping")
    op.drop_index("ix_ota_mapping_org_id", table_name="ota_mapping")
    op.drop_table("ota_mapping")
