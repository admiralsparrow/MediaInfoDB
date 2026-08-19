from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folder_id: Mapped[int] = mapped_column(ForeignKey("scanned_folders.id", ondelete="CASCADE"))
    file_path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    relative_path: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    container_format: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    overall_bitrate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    file_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_group: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    stream_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    hybrid: Mapped[bool] = mapped_column(Boolean, default=False)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    folder = relationship("ScannedFolder", back_populates="media_files")
    video_tracks = relationship("VideoTrack", back_populates="media_file", cascade="all, delete-orphan")
    audio_tracks = relationship("AudioTrack", back_populates="media_file", cascade="all, delete-orphan")
    subtitle_tracks = relationship("SubtitleTrack", back_populates="media_file", cascade="all, delete-orphan")
