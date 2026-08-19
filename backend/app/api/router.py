from fastapi import APIRouter

from app.api.browse import router as browse_router
from app.api.folders import router as folders_router
from app.api.libraries import router as libraries_router
from app.api.logs import router as logs_router
from app.api.media import router as media_router
from app.api.queue import router as queue_router
from app.api.status import router as status_router

api_router = APIRouter()
api_router.include_router(browse_router, prefix="/browse", tags=["browse"])
api_router.include_router(libraries_router, prefix="/libraries", tags=["libraries"])
api_router.include_router(folders_router, prefix="/folders", tags=["folders"])
api_router.include_router(media_router, prefix="/media", tags=["media"])
api_router.include_router(queue_router, prefix="/queue", tags=["queue"])
api_router.include_router(logs_router, prefix="/logs", tags=["logs"])
api_router.include_router(status_router, tags=["status"])
