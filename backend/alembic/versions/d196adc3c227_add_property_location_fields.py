"""add property location fields

Revision ID: d196adc3c227
Revises: 0027
Create Date: 2026-05-06 06:48:58.492263

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd196adc3c227'
down_revision: Union[str, None] = '0027'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('property', sa.Column('city', sa.String(100), nullable=True))
    op.add_column('property', sa.Column('state', sa.String(100), nullable=True))
    op.add_column('property', sa.Column('country', sa.String(100), nullable=True))
    op.add_column('property', sa.Column('postal_code', sa.String(20), nullable=True))
    op.add_column('property', sa.Column('latitude', sa.Numeric(10, 8), nullable=True))
    op.add_column('property', sa.Column('longitude', sa.Numeric(11, 8), nullable=True))


def downgrade() -> None:
    op.drop_column('property', 'city')
    op.drop_column('property', 'state')
    op.drop_column('property', 'country')
    op.drop_column('property', 'postal_code')
    op.drop_column('property', 'latitude')
    op.drop_column('property', 'longitude')
