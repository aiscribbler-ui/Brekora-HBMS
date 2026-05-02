"""add parse_metric table"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0024"
down_revision: Union[str, None, Sequence[str]] = ("0011", "0023")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parse_metric",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ota_source", sa.String(50), nullable=False, index=True),
        sa.Column("total_parsed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("successful", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("avg_confidence", sa.Numeric(4, 3), nullable=False, server_default=sa.text("0.0")),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("ota_source", "date", name="uq_parse_metric_source_date"),
    )


def downgrade() -> None:
    op.drop_table("parse_metric")
