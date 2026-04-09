"""add plans

Revision ID: 39ce8fe0e15f
Revises: 5cd1209b31dd
Create Date: 2026-04-09 12:12:09.199606

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '39ce8fe0e15f'
down_revision: Union[str, None] = '5cd1209b31dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create plans table
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Add plan_id to coach_messages, sessions, themes (simple add_column, no constraint changes)
    op.add_column('coach_messages', sa.Column('plan_id', sa.Integer(), nullable=True))
    op.add_column('sessions',       sa.Column('plan_id', sa.Integer(), nullable=True))
    op.add_column('themes',         sa.Column('plan_id', sa.Integer(), nullable=True))

    # settings: add plan_id + swap unique constraint using batch mode (SQLite requirement)
    with op.batch_alter_table('settings') as batch_op:
        batch_op.add_column(sa.Column('plan_id', sa.Integer(), nullable=True))
        batch_op.drop_constraint('uq_setting_user_key', type_='unique')
        batch_op.create_unique_constraint('uq_setting_plan_key', ['plan_id', 'key'])


def downgrade() -> None:
    with op.batch_alter_table('settings') as batch_op:
        batch_op.drop_constraint('uq_setting_plan_key', type_='unique')
        batch_op.create_unique_constraint('uq_setting_user_key', ['user_id', 'key'])
        batch_op.drop_column('plan_id')

    op.drop_column('themes',         'plan_id')
    op.drop_column('sessions',       'plan_id')
    op.drop_column('coach_messages', 'plan_id')
    op.drop_table('plans')
