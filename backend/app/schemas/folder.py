from datetime import datetime

from pydantic import BaseModel, field_validator


class FolderCreate(BaseModel):
    path: str
    library_ids: list[int]
    scan_interval_minutes: int | None = None

    @field_validator("library_ids")
    @classmethod
    def at_least_one_library(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("At least one library is required")
        return v


class FolderUpdate(BaseModel):
    enabled: bool | None = None
    scan_interval_minutes: int | None = None
    library_ids: list[int] | None = None


class FolderResponse(BaseModel):
    id: int
    path: str
    library_ids: list[int] = []
    added_at: datetime
    last_scanned: datetime | None
    scan_interval_minutes: int | None
    enabled: bool
    file_count: int

    model_config = {"from_attributes": True}

    @classmethod
    def from_folder(cls, folder) -> "FolderResponse":
        return cls(
            id=folder.id,
            path=folder.path,
            library_ids=[lib.id for lib in folder.libraries],
            added_at=folder.added_at,
            last_scanned=folder.last_scanned,
            scan_interval_minutes=folder.scan_interval_minutes,
            enabled=folder.enabled,
            file_count=folder.file_count,
        )
