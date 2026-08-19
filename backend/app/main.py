import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

from app.api.router import api_router
from app.worker.scheduler import start_scheduler, shutdown_scheduler
from app.worker.tasks import recover_interrupted_queue


async def _repair_file_path_index():
    """Remove duplicate media_files rows and reindex to fix any index corruption."""
    from app.database import engine
    from sqlalchemy import text

    try:
        async with engine.begin() as conn:
            await conn.execute(text(
                "DELETE FROM media_files a USING media_files b "
                "WHERE a.id > b.id AND a.file_path = b.file_path"
            ))
            await conn.execute(text("REINDEX INDEX media_files_file_path_key"))
    except Exception as e:
        logger.warning("Failed to repair file_path index (non-fatal): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import settings, _DEFAULT_DB_PASSWORD
    if _DEFAULT_DB_PASSWORD in settings.DATABASE_URL:
        logger.warning(
            "DATABASE_URL uses the default password — change DB_PASSWORD before exposing this service"
        )
    await _repair_file_path_index()
    await recover_interrupted_queue()
    await start_scheduler()
    yield
    await shutdown_scheduler()


from pathlib import Path

_version_file = Path(__file__).resolve().parents[2] / "VERSION"
__version__ = _version_file.read_text().strip() if _version_file.exists() else "dev"

app = FastAPI(title="MediaInfoDB", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
