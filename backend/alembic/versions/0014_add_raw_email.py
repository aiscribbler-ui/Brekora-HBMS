"""add raw_email

Revision ID: 0014
Revises: 0009
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raw_email",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gmail_message_id", sa.String(length=255), nullable=False),
        sa.Column("ota_source", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("sender", sa.String(length=255), nullable=True),
        sa.Column("recipient", sa.String(length=255), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
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
        "ix_raw_email_org_id",
        "raw_email",
        ["org_id"],
        unique=False,
    )
    op.create_index(
        "ix_raw_email_gmail_message_id",
        "raw_email",
        ["gmail_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_raw_email_status",
        "raw_email",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_raw_email_status", table_name="raw_email")
    op.drop_index("ix_raw_email_gmail_message_id", table_name="raw_email")
    op.drop_index("ix_raw_email_org_id", table_name="raw_email")
    op.drop_table("raw_email")
