"""add totp columns to user table"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0017"
down_revision: Union[str, None, Sequence[str]] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("totp_secret", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "totp_secret")
