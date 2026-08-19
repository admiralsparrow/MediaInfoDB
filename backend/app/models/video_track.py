from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class VideoTrack(Base):
    __tablename__ = "video_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    media_file_id: Mapped[int] = mapped_column(ForeignKey("media_files.id", ondelete="CASCADE"))
    track_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    codec: Mapped[str | None] = mapped_column(String, nullable=True)
    bitrate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    framerate: Mapped[float | None] = mapped_column(Numeric(7, 3), nullable=True)
    hdr10: Mapped[bool] = mapped_column(Boolean, default=False)
    dolby_vision: Mapped[bool] = mapped_column(Boolean, default=False)
    dv_layer: Mapped[str | None] = mapped_column(String, nullable=True)
    dv_profile: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    hdr10_plus: Mapped[bool] = mapped_column(Boolean, default=False)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    track_name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_forced: Mapped[bool] = mapped_column(Boolean, default=False)
    display_aspect_ratio: Mapped[str | None] = mapped_column(String, nullable=True)
    bit_depth: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    color_primaries: Mapped[str | None] = mapped_column(String, nullable=True)
    transfer_characteristics: Mapped[str | None] = mapped_column(String, nullable=True)
    encoding_library: Mapped[str | None] = mapped_column(String, nullable=True)
    scan_type: Mapped[str | None] = mapped_column(String, nullable=True)
    chroma_subsampling: Mapped[str | None] = mapped_column(String, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String, nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    media_file = relationship("MediaFile", back_populates="video_tracks")
