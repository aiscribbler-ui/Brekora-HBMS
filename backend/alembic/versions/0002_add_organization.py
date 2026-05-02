"""add organization

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def upgrade() -> None:
    op.create_table(
        "organization",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
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
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        "ix_organization_slug", "organization", ["slug"], unique=False
    )

    op.execute(
        sa.text(
            "INSERT INTO organization (id, name, slug) VALUES (:id, :name, :slug)"
        ).bindparams(
            id=DEFAULT_ORG_ID,
            name="Brekora",
            slug="brekora",
        )
    )


def downgrade() -> None:
    op.drop_index("ix_organization_slug", table_name="organization")
    op.drop_table("organization")
