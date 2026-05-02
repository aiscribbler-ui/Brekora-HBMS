"""add pricing models

Revision ID: 0013
Revises: 0015
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rate_plan",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("discount_type", sa.String(length=20), nullable=False, server_default=sa.text("'percentage'")),
        sa.Column("discount_value", sa.Numeric(precision=12, scale=2), nullable=False, server_default=sa.text("'0.00'")),
        sa.Column("min_nights", sa.Integer(), nullable=True),
        sa.Column("max_nights", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.UniqueConstraint("org_id", "code", name="uq_rate_plan_org_code"),
    )
    op.create_index("ix_rate_plan_org_id", "rate_plan", ["org_id"], unique=False)

    op.create_table(
        "seasonal_calendar",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("multiplier", sa.Numeric(precision=5, scale=2), nullable=False, server_default=sa.text("'1.00'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
    )
    op.create_index("ix_seasonal_calendar_org_id", "seasonal_calendar", ["org_id"], unique=False)
    op.create_index("ix_seasonal_calendar_start_date", "seasonal_calendar", ["start_date"], unique=False)
    op.create_index("ix_seasonal_calendar_end_date", "seasonal_calendar", ["end_date"], unique=False)

    op.create_table(
        "promo_code",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("discount_type", sa.String(length=20), nullable=False, server_default=sa.text("'percentage'")),
        sa.Column("discount_value", sa.Numeric(precision=12, scale=2), nullable=False, server_default=sa.text("'0.00'")),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default=sa.text("'0'")),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("applicable_booking_types", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.UniqueConstraint("org_id", "code", name="uq_promo_code_org_code"),
    )
    op.create_index("ix_promo_code_org_id", "promo_code", ["org_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_promo_code_org_id", table_name="promo_code")
    op.drop_table("promo_code")
    op.drop_index("ix_seasonal_calendar_end_date", table_name="seasonal_calendar")
    op.drop_index("ix_seasonal_calendar_start_date", table_name="seasonal_calendar")
    op.drop_index("ix_seasonal_calendar_org_id", table_name="seasonal_calendar")
    op.drop_table("seasonal_calendar")
    op.drop_index("ix_rate_plan_org_id", table_name="rate_plan")
    op.drop_table("rate_plan")
