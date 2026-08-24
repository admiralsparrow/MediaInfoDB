"""Add folder_paths table for fast folder filter lookups

Revision ID: 006
Revises: 005
Create Date: 2026-08-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name='folder_paths'"
    ))
    if not result.fetchone():
        op.create_table(
            "folder_paths",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("folder_id", sa.Integer(), sa.ForeignKey("scanned_folders.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("path", sa.String(), nullable=False),
            sa.Column("file_count", sa.Integer(), server_default="0", nullable=False),
            sa.UniqueConstraint("folder_id", "path", name="uq_folder_paths_folder_path"),
        )

    # Populate from existing data if table is empty
    existing_count = conn.execute(sa.text("SELECT COUNT(*) FROM folder_paths")).scalar()
    if existing_count:
        return

    rows = conn.execute(sa.text(
        "SELECT folder_id, relative_path FROM media_files "
        "WHERE relative_path IS NOT NULL AND folder_id IS NOT NULL AND position('/' in relative_path) > 0"
    )).fetchall()

    # Build counts: (folder_id, dir_prefix) -> count
    from collections import defaultdict
    counts: dict[tuple[int, str], int] = defaultdict(int)
    for folder_id, relative_path in rows:
        parts = relative_path.split("/")
        # Each prefix up to but not including the filename
        for i in range(1, len(parts)):
            counts[(folder_id, "/".join(parts[:i]))] += 1

    if counts:
        # Batch insert
        insert_data = [
            {"folder_id": k[0], "path": k[1], "file_count": v}
            for k, v in counts.items()
        ]
        folder_paths = sa.table(
            "folder_paths",
            sa.column("folder_id", sa.Integer),
            sa.column("path", sa.String),
            sa.column("file_count", sa.Integer),
        )
        batch_size = 1000
        for i in range(0, len(insert_data), batch_size):
            conn.execute(folder_paths.insert(), insert_data[i:i + batch_size])


def downgrade() -> None:
    op.drop_table("folder_paths")
