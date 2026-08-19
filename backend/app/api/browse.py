from fastapi import APIRouter, HTTPException, Query

from app.schemas.browse import BrowseEntry
from app.services.folder_browser import folder_browser

router = APIRouter()


@router.get("", response_model=list[BrowseEntry])
async def browse_directory(path: str | None = Query(default=None)):
    if path is None:
        return folder_browser.get_roots()

    try:
        return folder_browser.list_directory(path)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Path outside allowed roots")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Directory not found")
