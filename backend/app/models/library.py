from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

library_folders = Table(
    "library_folders",
    Base.metadata,
    Column("library_id", Integer, ForeignKey("libraries.id", ondelete="CASCADE"), primary_key=True),
    Column("folder_id", Integer, ForeignKey("scanned_folders.id", ondelete="CASCADE"), primary_key=True),
)


class Library(Base):
    __tablename__ = "libraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    folders = relationship("ScannedFolder", secondary=library_folders, back_populates="libraries")
