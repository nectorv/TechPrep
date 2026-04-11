"""add explanation to questions

Revision ID: 94c40614ba55
Revises: 6180a441a4ba
Create Date: 2026-04-11 16:22:13.174847

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94c40614ba55'
down_revision: Union[str, None] = '6180a441a4ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('explanation', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('questions', 'explanation')
