"""add_user_property

Revision ID: 93080abe4c6b
Revises: 851f370ef59e
Create Date: 2026-05-07 09:14:29.470913

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93080abe4c6b'
down_revision: Union[str, None] = 'd196adc3c227'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('user_property',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('property_id', sa.UUID(), nullable=False),
    sa.Column('role_at_property', sa.String(length=50), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['property_id'], ['property.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'property_id'),
    sa.UniqueConstraint('user_id', 'property_id', name='uq_user_property')
    )
    op.create_index('ix_user_property_property_id', 'user_property', ['property_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_property_property_id', table_name='user_property')
    op.drop_table('user_property')
