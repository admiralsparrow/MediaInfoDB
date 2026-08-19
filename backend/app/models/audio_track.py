from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AudioTrack(Base):
    __tablename__ = "audio_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    media_file_id: Mapped[int] = mapped_column(ForeignKey("media_files.id", ondelete="CASCADE"))
    track_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    codec: Mapped[str | None] = mapped_column(String, nullable=True)
    bitrate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    channel_layout: Mapped[str | None] = mapped_column(String, nullable=True)
    channels: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    track_name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_original: Mapped[bool] = mapped_column(Boolean, default=False)
    is_forced: Mapped[bool] = mapped_column(Boolean, default=False)
    is_commentary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_atmos: Mapped[bool] = mapped_column(Boolean, default=False)
    sample_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compression_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    media_file = relationship("MediaFile", back_populates="audio_tracks")
