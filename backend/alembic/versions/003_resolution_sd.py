"""Convert resolution values below 480p to SD

Revision ID: 003
Revises: 002
Create Date: 2026-08-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text("""
            UPDATE video_tracks
            SET resolution = 'SD'
            WHERE resolution IS NOT NULL
              AND resolution != 'SD'
              AND resolution NOT IN ('480p', '540p', '720p', '1080p', '2160p', '4320p')
        """)
    )


def downgrade() -> None:
    # Cannot reliably restore original values; set to NULL
    op.execute(
        sa.text("""
            UPDATE video_tracks
            SET resolution = NULL
            WHERE resolution = 'SD'
        """)
    )
