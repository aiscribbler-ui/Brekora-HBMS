"""add listing manager role

Revision ID: 0027
Revises: 0026
Create Date: 2026-05-04 00:00:00.000000

"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def upgrade() -> None:
    # Insert ListingManager role if it does not already exist
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT id FROM role WHERE org_id = :org_id AND name = :name"
        ).bindparams(org_id=DEFAULT_ORG_ID, name="ListingManager")
    )
    if result.scalar_one_or_none() is None:
        role_id = uuid.uuid4()
        conn.execute(
            sa.text(
                "INSERT INTO role (id, org_id, name, description) VALUES (:id, :org_id, :name, :description)"
            ).bindparams(
                id=role_id,
                org_id=DEFAULT_ORG_ID,
                name="ListingManager",
                description="Manages OTA listings and content across all properties",
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM role WHERE org_id = :org_id AND name = :name"
        ).bindparams(org_id=DEFAULT_ORG_ID, name="ListingManager")
    )
