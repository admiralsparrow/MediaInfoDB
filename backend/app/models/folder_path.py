from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FolderPath(Base):
    __tablename__ = "folder_paths"
    __table_args__ = (
        UniqueConstraint("folder_id", "path", name="uq_folder_paths_folder_path"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folder_id: Mapped[int] = mapped_column(Integer, ForeignKey("scanned_folders.id", ondelete="CASCADE"), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, default=0)

    folder = relationship("ScannedFolder", back_populates="folder_paths")
