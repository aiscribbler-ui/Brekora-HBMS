"""add google_id to user

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-02 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user", sa.Column("google_id", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("user", "google_id")
