"""telegram_id biginteger

Revision ID: 6180a441a4ba
Revises: b9bef45b014d
Create Date: 2026-04-10 22:50:39.616791

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6180a441a4ba'
down_revision: Union[str, None] = 'b9bef45b014d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.alter_column('users', 'telegram_id',
                   existing_type=sa.INTEGER(),
                   type_=sa.BigInteger(),
                   existing_nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.alter_column('users', 'telegram_id',
                   existing_type=sa.BigInteger(),
                   type_=sa.INTEGER(),
                   existing_nullable=True)
