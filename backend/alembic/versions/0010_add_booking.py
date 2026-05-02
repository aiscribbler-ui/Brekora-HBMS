"""add booking

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "booking",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_type", sa.String(length=20), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False, server_default=sa.text("'direct'")),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("guest_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("check_in", sa.Date(), nullable=False),
        sa.Column("check_out", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending_payment'"),
        ),
        sa.Column("line_items", postgresql.JSONB(), nullable=True),
        sa.Column("gross_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default=sa.text("'0.00'")),
        sa.Column("discount_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default=sa.text("'0.00'")),
        sa.Column("tax_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default=sa.text("'0.00'")),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default=sa.text("'0.00'")),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'INR'")),
        sa.Column("cancellation_policy_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("partner_attribution_id", sa.String(length=255), nullable=True),
        sa.Column("payment_state", sa.String(length=50), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=255), nullable=True),
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
            ["guest_id"],
            ["user.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("org_id", "idempotency_key", name="uq_booking_org_idempotency"),
    )
    op.create_index("ix_booking_org_id", "booking", ["org_id"], unique=False)
    op.create_index("ix_booking_property_id", "booking", ["property_id"], unique=False)
    op.create_index("ix_booking_guest_id", "booking", ["guest_id"], unique=False)
    op.create_index("ix_booking_check_in", "booking", ["check_in"], unique=False)
    op.create_index("ix_booking_status", "booking", ["status"], unique=False)
    op.create_index("ix_booking_idempotency_key", "booking", ["idempotency_key"], unique=False)

    op.create_table(
        "booking_line_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("'1'")),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False, server_default=sa.text("'0.00'")),
        sa.Column("nights", sa.Integer(), nullable=False, server_default=sa.text("'1'")),
        sa.Column("total_price", sa.Numeric(precision=12, scale=2), nullable=False, server_default=sa.text("'0.00'")),
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
            ["booking_id"],
            ["booking.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_booking_line_item_booking_id", "booking_line_item", ["booking_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_booking_line_item_booking_id", table_name="booking_line_item")
    op.drop_table("booking_line_item")
    op.drop_index("ix_booking_idempotency_key", table_name="booking")
    op.drop_index("ix_booking_status", table_name="booking")
    op.drop_index("ix_booking_check_in", table_name="booking")
    op.drop_index("ix_booking_guest_id", table_name="booking")
    op.drop_index("ix_booking_property_id", table_name="booking")
    op.drop_index("ix_booking_org_id", table_name="booking")
    op.drop_table("booking")
