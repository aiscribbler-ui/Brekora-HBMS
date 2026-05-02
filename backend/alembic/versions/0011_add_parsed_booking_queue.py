"""add parsed_booking_queue

Revision ID: 0011
Revises: 0015
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parsed_booking_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("raw_email_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ota_reference_id", sa.String(length=255), nullable=True),
        sa.Column("parsed_data", postgresql.JSONB(), nullable=True),
        sa.Column(
            "confidence_score",
            sa.Numeric(precision=4, scale=3),
            nullable=False,
            server_default=sa.text("'0.000'"),
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("confirmed_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            ["raw_email_id"],
            ["raw_email.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["manager_id"],
            ["user.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_booking_id"],
            ["booking.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_parsed_booking_queue_org_id",
        "parsed_booking_queue",
        ["org_id"],
        unique=False,
    )
    op.create_index(
        "ix_parsed_booking_queue_status",
        "parsed_booking_queue",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_parsed_booking_queue_source_type",
        "parsed_booking_queue",
        ["source_type"],
        unique=False,
    )
    op.create_index(
        "ix_parsed_booking_queue_raw_email_id",
        "parsed_booking_queue",
        ["raw_email_id"],
        unique=False,
    )
    op.create_index(
        "ix_parsed_booking_queue_ota_reference_id",
        "parsed_booking_queue",
        ["ota_reference_id"],
        unique=False,
    )
    op.create_index(
        "ix_parsed_booking_queue_manager_id",
        "parsed_booking_queue",
        ["manager_id"],
        unique=False,
    )
    op.create_index(
        "ix_parsed_booking_queue_confirmed_booking_id",
        "parsed_booking_queue",
        ["confirmed_booking_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_parsed_booking_queue_confirmed_booking_id",
        table_name="parsed_booking_queue",
    )
    op.drop_index(
        "ix_parsed_booking_queue_manager_id",
        table_name="parsed_booking_queue",
    )
    op.drop_index(
        "ix_parsed_booking_queue_ota_reference_id",
        table_name="parsed_booking_queue",
    )
    op.drop_index(
        "ix_parsed_booking_queue_raw_email_id",
        table_name="parsed_booking_queue",
    )
    op.drop_index(
        "ix_parsed_booking_queue_source_type",
        table_name="parsed_booking_queue",
    )
    op.drop_index(
        "ix_parsed_booking_queue_status",
        table_name="parsed_booking_queue",
    )
    op.drop_index(
        "ix_parsed_booking_queue_org_id",
        table_name="parsed_booking_queue",
    )
    op.drop_table("parsed_booking_queue")
