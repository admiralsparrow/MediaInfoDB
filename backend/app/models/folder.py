from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ScannedFolder(Base):
    __tablename__ = "scanned_folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_scanned: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scan_interval_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    file_count: Mapped[int] = mapped_column(Integer, default=0)

    libraries = relationship("Library", secondary="library_folders", back_populates="folders")
    media_files = relationship("MediaFile", back_populates="folder", cascade="all, delete-orphan")
    folder_paths = relationship("FolderPath", back_populates="folder", cascade="all, delete-orphan")
    scan_jobs = relationship("ScanJob", back_populates="folder", cascade="all, delete-orphan")
