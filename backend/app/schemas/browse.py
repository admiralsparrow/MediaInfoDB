from pydantic import BaseModel


class BrowseEntry(BaseModel):
    name: str
    path: str
    has_children: bool
