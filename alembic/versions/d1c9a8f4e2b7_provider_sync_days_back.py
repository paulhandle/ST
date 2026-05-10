"""provider sync days back

Revision ID: d1c9a8f4e2b7
Revises: c2a9d8e1b4f3
Create Date: 2026-05-10 19:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1c9a8f4e2b7"
down_revision: Union[str, Sequence[str], None] = "c2a9d8e1b4f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("provider_sync_jobs", sa.Column("sync_days_back", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("provider_sync_jobs", "sync_days_back")
