"""Add phase column to scan_jobs

Revision ID: 002
Revises: 001
Create Date: 2026-08-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns WHERE table_name='scan_jobs' AND column_name='phase'"
    ))
    if not result.fetchone():
        op.add_column("scan_jobs", sa.Column("phase", sa.String(), server_default="scanning", nullable=False))


def downgrade() -> None:
    op.drop_column("scan_jobs", "phase")
