"""add modification_log to booking"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0025"
down_revision: Union[str, None, Sequence[str]] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "booking",
        sa.Column("modification_log", JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("booking", "modification_log")
