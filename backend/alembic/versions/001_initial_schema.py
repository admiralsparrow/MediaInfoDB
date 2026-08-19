"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-08-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "libraries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scanned_folders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("path", sa.String(), nullable=False, unique=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_scanned", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scan_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), default=True),
        sa.Column("file_count", sa.Integer(), default=0),
    )

    op.create_table(
        "library_folders",
        sa.Column("library_id", sa.Integer(), sa.ForeignKey("libraries.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("folder_id", sa.Integer(), sa.ForeignKey("scanned_folders.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "media_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("folder_id", sa.Integer(), sa.ForeignKey("scanned_folders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False, unique=True),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("container_format", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("overall_bitrate", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("scanned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("file_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra", postgresql.JSONB(), server_default="{}"),
        sa.Column("relative_path", sa.String(), nullable=True),
        sa.Column("release_group", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("year", sa.SmallInteger(), nullable=True),
        sa.Column("stream_count", sa.SmallInteger(), nullable=True),
        sa.Column("hybrid", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index("idx_media_files_folder", "media_files", ["folder_id"])
    op.create_index("ix_media_files_relative_path", "media_files", ["relative_path"])

    op.create_table(
        "video_tracks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("media_file_id", sa.Integer(), sa.ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_index", sa.SmallInteger(), nullable=False),
        sa.Column("codec", sa.String(), nullable=True),
        sa.Column("bitrate", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("framerate", sa.Numeric(7, 3), nullable=True),
        sa.Column("hdr10", sa.Boolean(), default=False),
        sa.Column("dolby_vision", sa.Boolean(), default=False),
        sa.Column("dv_layer", sa.String(), nullable=True),
        sa.Column("dv_profile", sa.SmallInteger(), nullable=True),
        sa.Column("hdr10_plus", sa.Boolean(), default=False),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("track_name", sa.String(), nullable=True),
        sa.Column("is_default", sa.Boolean(), default=False),
        sa.Column("is_forced", sa.Boolean(), default=False),
        sa.Column("extra", postgresql.JSONB(), server_default="{}"),
        sa.Column("display_aspect_ratio", sa.String(), nullable=True),
        sa.Column("bit_depth", sa.SmallInteger(), nullable=True),
        sa.Column("color_primaries", sa.String(), nullable=True),
        sa.Column("transfer_characteristics", sa.String(), nullable=True),
        sa.Column("encoding_library", sa.String(), nullable=True),
        sa.Column("scan_type", sa.String(), nullable=True),
        sa.Column("chroma_subsampling", sa.String(), nullable=True),
        sa.Column("resolution", sa.String(), nullable=True),
    )
    op.create_index("idx_video_tracks_file", "video_tracks", ["media_file_id"])

    op.create_table(
        "audio_tracks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("media_file_id", sa.Integer(), sa.ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_index", sa.SmallInteger(), nullable=False),
        sa.Column("codec", sa.String(), nullable=True),
        sa.Column("bitrate", sa.Integer(), nullable=True),
        sa.Column("channel_layout", sa.String(), nullable=True),
        sa.Column("channels", sa.SmallInteger(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("track_name", sa.String(), nullable=True),
        sa.Column("is_default", sa.Boolean(), default=False),
        sa.Column("is_original", sa.Boolean(), default=False),
        sa.Column("is_forced", sa.Boolean(), default=False),
        sa.Column("is_commentary", sa.Boolean(), default=False),
        sa.Column("is_atmos", sa.Boolean(), server_default="false"),
        sa.Column("extra", postgresql.JSONB(), server_default="{}"),
        sa.Column("sample_rate", sa.Integer(), nullable=True),
        sa.Column("compression_mode", sa.String(), nullable=True),
    )
    op.create_index("idx_audio_tracks_file", "audio_tracks", ["media_file_id"])

    op.create_table(
        "subtitle_tracks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("media_file_id", sa.Integer(), sa.ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_index", sa.SmallInteger(), nullable=False),
        sa.Column("codec", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("track_name", sa.String(), nullable=True),
        sa.Column("is_default", sa.Boolean(), default=False),
        sa.Column("is_forced", sa.Boolean(), default=False),
        sa.Column("is_hearing_impaired", sa.Boolean(), default=False),
        sa.Column("extra", postgresql.JSONB(), server_default="{}"),
    )
    op.create_index("idx_subtitle_tracks_file", "subtitle_tracks", ["media_file_id"])

    op.create_table(
        "scan_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("folder_id", sa.Integer(), sa.ForeignKey("scanned_folders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), default="running"),
        sa.Column("files_found", sa.Integer(), default=0),
        sa.Column("files_scanned", sa.Integer(), default=0),
        sa.Column("error_message", sa.String(), nullable=True),
    )
    op.create_index("ix_scan_jobs_status", "scan_jobs", ["status"])

    op.create_table(
        "scan_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("folder_id", sa.Integer(), sa.ForeignKey("scanned_folders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("relative_path", sa.String(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(), server_default="'pending'", nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("media_file_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_scan_queue_folder_status_priority", "scan_queue", ["folder_id", "status", sa.text("priority DESC")])
    op.create_index("ix_scan_queue_status", "scan_queue", ["status"])
    op.execute(
        "CREATE UNIQUE INDEX ix_scan_queue_file_path_active "
        "ON scan_queue (file_path) "
        "WHERE status IN ('pending', 'processing')"
    )


def downgrade() -> None:
    op.drop_table("scan_queue")
    op.drop_table("scan_jobs")
    op.drop_table("subtitle_tracks")
    op.drop_table("audio_tracks")
    op.drop_table("video_tracks")
    op.drop_table("media_files")
    op.drop_table("library_folders")
    op.drop_table("scanned_folders")
    op.drop_table("libraries")
