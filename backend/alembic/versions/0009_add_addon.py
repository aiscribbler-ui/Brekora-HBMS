"""add add_on and add_on_capacity tables, plus FK from package_add_on

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "add_on",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "type",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'day'"),
        ),
        sa.Column(
            "default_capacity", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "unit_price",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
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
            ["org_id"], ["organization.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["property_id"], ["property.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_add_on_org_id", "add_on", ["org_id"], unique=False)
    op.create_index(
        "ix_add_on_property_id", "add_on", ["property_id"], unique=False
    )

    op.create_table(
        "add_on_capacity",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("add_on_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("slot_time", sa.Time(), nullable=True),
        sa.Column(
            "available_capacity",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_capacity",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
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
            ["add_on_id"], ["add_on.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_add_on_capacity_add_on_id",
        "add_on_capacity",
        ["add_on_id"],
        unique=False,
    )
    op.create_index(
        "ix_add_on_capacity_date",
        "add_on_capacity",
        ["date"],
        unique=False,
    )
    op.create_index(
        "ix_add_on_capacity_add_on_id_date",
        "add_on_capacity",
        ["add_on_id", "date"],
        unique=False,
    )

    # Add FK to existing package_add_on.add_on_id
    op.create_foreign_key(
        "fk_package_add_on_add_on_id",
        "package_add_on",
        "add_on",
        ["add_on_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_package_add_on_add_on_id", "package_add_on", type_="foreignkey"
    )
    op.drop_index(
        "ix_add_on_capacity_add_on_id_date", table_name="add_on_capacity"
    )
    op.drop_index("ix_add_on_capacity_date", table_name="add_on_capacity")
    op.drop_index(
        "ix_add_on_capacity_add_on_id", table_name="add_on_capacity"
    )
    op.drop_table("add_on_capacity")
    op.drop_index("ix_add_on_property_id", table_name="add_on")
    op.drop_index("ix_add_on_org_id", table_name="add_on")
    op.drop_table("add_on")
