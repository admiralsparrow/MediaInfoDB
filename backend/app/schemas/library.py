from datetime import datetime

from pydantic import BaseModel


class LibraryCreate(BaseModel):
    name: str


class LibraryUpdate(BaseModel):
    name: str | None = None


class LibraryResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LibraryFolderInfo(BaseModel):
    id: int
    path: str
    file_count: int
    enabled: bool

    model_config = {"from_attributes": True}


class LibraryDetailResponse(LibraryResponse):
    folders: list[LibraryFolderInfo]
