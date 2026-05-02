"""add cancellation_policy

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cancellation_policy",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("free_cancellation_hours", sa.Integer(), nullable=True),
        sa.Column("partial_refund_hours", sa.Integer(), nullable=True),
        sa.Column(
            "partial_refund_percentage",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
        sa.Column("non_refundable_hours", sa.Integer(), nullable=True),
        sa.Column(
            "is_non_refundable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
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
    )
    op.create_index(
        "ix_cancellation_policy_org_id",
        "cancellation_policy",
        ["org_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cancellation_policy_org_id", table_name="cancellation_policy"
    )
    op.drop_table("cancellation_policy")
