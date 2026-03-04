"""add role to users

Revision ID: d1989e15b2d5
Revises: 0c0d5409bd16
Create Date: 2026-03-04 17:26:42.582670

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1989e15b2d5'
down_revision: Union[str, Sequence[str], None] = '0c0d5409bd16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("role", sa.String(length=20), nullable=False, server_default="operator"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "role")
