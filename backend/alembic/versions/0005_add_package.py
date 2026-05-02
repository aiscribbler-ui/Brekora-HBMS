"""add package, package_composition, package_add_on

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "package",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'draft'")),
        sa.Column(
            "base_price", sa.Numeric(precision=12, scale=2), nullable=False, server_default=sa.text("0.00")
        ),
        sa.Column("dynamic_pricing_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("date_constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("max_occupancy", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["property_id"], ["property.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_package_org_id", "package", ["org_id"], unique=False)
    op.create_index("ix_package_property_id", "package", ["property_id"], unique=False)

    op.create_table(
        "package_composition",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("nights", sa.Integer(), nullable=False, server_default=sa.text("1")),
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
        sa.ForeignKeyConstraint(["package_id"], ["package.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_type_id"], ["room_type.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_package_composition_org_id", "package_composition", ["org_id"], unique=False)
    op.create_index("ix_package_composition_package_id", "package_composition", ["package_id"], unique=False)
    op.create_index("ix_package_composition_room_type_id", "package_composition", ["room_type_id"], unique=False)

    op.create_table(
        "package_add_on",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("add_on_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_included", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.ForeignKeyConstraint(["package_id"], ["package.id"], ondelete="CASCADE"),
        # FK to add_on will be added in migration 0006 (A-011)
    )
    op.create_index("ix_package_add_on_org_id", "package_add_on", ["org_id"], unique=False)
    op.create_index("ix_package_add_on_package_id", "package_add_on", ["package_id"], unique=False)
    op.create_index("ix_package_add_on_add_on_id", "package_add_on", ["add_on_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_package_add_on_add_on_id", table_name="package_add_on")
    op.drop_index("ix_package_add_on_package_id", table_name="package_add_on")
    op.drop_index("ix_package_add_on_org_id", table_name="package_add_on")
    op.drop_table("package_add_on")

    op.drop_index("ix_package_composition_room_type_id", table_name="package_composition")
    op.drop_index("ix_package_composition_package_id", table_name="package_composition")
    op.drop_index("ix_package_composition_org_id", table_name="package_composition")
    op.drop_table("package_composition")

    op.drop_index("ix_package_property_id", table_name="package")
    op.drop_index("ix_package_org_id", table_name="package")
    op.drop_table("package")
