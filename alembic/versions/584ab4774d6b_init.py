"""init

Revision ID: 584ab4774d6b
Revises:
Create Date: 2026-02-26 16:53:54.909466

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "584ab4774d6b"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("mgmt_ip", sa.String(length=64), nullable=False),
        sa.Column("vendor", sa.String(length=64), nullable=True),
        sa.Column("site_id", sa.String(length=64), nullable=True),
        sa.Column("role", sa.String(length=64), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("area", sa.String(length=128), nullable=True),
        sa.Column("software_version", sa.String(length=64), nullable=True),
        sa.Column("platform", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_devices_hostname"), "devices", ["hostname"], unique=True)
    op.create_index(op.f("ix_devices_mgmt_ip"), "devices", ["mgmt_ip"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_devices_mgmt_ip"), table_name="devices")
    op.drop_index(op.f("ix_devices_hostname"), table_name="devices")
    op.drop_table("devices")
