"""add telegram_link_codes

Revision ID: b9bef45b014d
Revises: 39ce8fe0e15f
Create Date: 2026-04-09 15:49:36.453464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9bef45b014d'
down_revision: Union[str, None] = '39ce8fe0e15f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('telegram_link_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=6), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_telegram_link_codes_code'), 'telegram_link_codes', ['code'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_telegram_link_codes_code'), table_name='telegram_link_codes')
    op.drop_table('telegram_link_codes')
