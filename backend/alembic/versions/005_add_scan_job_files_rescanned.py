"""Add files_rescanned and rescanned_file_paths columns to scan_jobs

Revision ID: 005
Revises: 004
Create Date: 2026-08-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns WHERE table_name='scan_jobs' AND column_name='files_rescanned'"
    ))
    if not result.fetchone():
        op.add_column("scan_jobs", sa.Column("files_rescanned", sa.Integer(), server_default="0", nullable=False))

    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns WHERE table_name='scan_jobs' AND column_name='rescanned_file_paths'"
    ))
    if not result.fetchone():
        op.add_column("scan_jobs", sa.Column("rescanned_file_paths", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("scan_jobs", "rescanned_file_paths")
    op.drop_column("scan_jobs", "files_rescanned")
