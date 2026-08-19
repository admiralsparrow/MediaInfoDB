# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dockerized web application that scans video files for media information (codecs, HDR formats, audio/subtitle tracks) and stores it in PostgreSQL for filterable browsing. Supports multiple libraries, each with multiple folder mappings.

## Architecture

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic migrations, pymediainfo, APScheduler
- **Frontend:** React 18, TypeScript, Vite, TanStack Query
- **Database:** PostgreSQL 16 (internal via Docker Compose or external via `DATABASE_URL`)
- **Infrastructure:** Docker Compose with nginx reverse proxy for frontend

### Key Design Patterns

- **Libraries:** Many-to-many relationship between libraries and folders via `library_folders` junction table. A folder must belong to at least one library. Removing a folder from its last library deletes the folder and its media files.
- **Extensibility:** Every track table has an `extra JSONB` column for new fields before they get promoted to typed columns via migration.
- **Filter system:** `backend/app/services/filter_builder.py` has a `FILTER_REGISTRY` dict that maps API query params to SQLAlchemy columns. Frontend's `filterDefinitions.ts` mirrors this. Adding a new filter = one entry in each. The `library_id` filter is handled separately via junction table join.
- **Security:** Folder browser is restricted to paths under `ALLOWED_BROWSE_ROOTS` with symlink-resolved path validation.
- **Scanning:** APScheduler runs in-process with FastAPI. Per-folder asyncio locks prevent overlapping scans. pymediainfo calls run in `asyncio.to_thread()`. Scan progress is exposed via `/api/v1/scans/active` and polled by the frontend for a progress banner.
- **Sort on track columns:** Sorting by video/audio track fields uses a subquery with `MIN`/`MAX` aggregation to avoid DISTINCT+ORDER BY conflicts.

## Commands

```bash
# Run everything (with internal PostgreSQL)
docker compose up --build

# Run with external database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db docker compose up --build backend frontend

# Backend dev (outside Docker)
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend dev (outside Docker)
cd frontend
npm install
npm run dev

# Create a new migration
cd backend
alembic revision --autogenerate -m "description"

# Run migration
cd backend
alembic upgrade head

# Clear database
docker compose exec db psql -U mediainfo -d mediainfo -c "TRUNCATE scan_jobs, subtitle_tracks, audio_tracks, video_tracks, media_files, library_folders, scanned_folders, libraries CASCADE;"
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://mediainfo:mediainfo_dev@db:5432/mediainfo` | DB connection |
| `DB_PASSWORD` | `mediainfo_dev` | PostgreSQL password (internal DB only) |
| `ALLOWED_BROWSE_ROOTS` | `/media` | Comma-separated paths the folder browser can access |
| `SCAN_INTERVAL_MINUTES` | `360` | Default interval between automatic re-scans |
| `MEDIA_PATH_1..3` | `/media` | Host paths mounted into container at `/media/library1..3` |

## Database Schema

`libraries` ←→ `scanned_folders` (many-to-many via `library_folders`) → `media_files` → `{video,audio,subtitle}_tracks` (cascade delete). `scan_jobs` tracks scan history per folder.

## Adding a New Media Info Field

1. Add column to the appropriate model in `backend/app/models/`
2. Create Alembic migration: `alembic revision --autogenerate -m "add field"`
3. Update `backend/app/services/scanner.py` to extract the field from pymediainfo
4. Add entry to `FILTER_REGISTRY` in `backend/app/services/filter_builder.py`
5. Add entry to `frontend/src/components/Filters/filterDefinitions.ts`
6. Add to the response schema in `backend/app/schemas/media_file.py`
7. Add to TypeScript types in `frontend/src/types/media.ts`
8. (Optional) Add column definition to `frontend/src/components/MediaTable/columns.ts`

## Adding a New Table Column (UI)

1. Add entry to `ALL_COLUMNS` in `frontend/src/components/MediaTable/columns.ts` with key, label, group, getValue, and optionally sortField
2. If sortField references a track table column, add it to `SORT_MAP` in `backend/app/api/media.py`
