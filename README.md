# MediaInfoDB

A self-hosted web application that scans video files for media information (codecs, HDR formats, audio/subtitle tracks) and stores it in PostgreSQL for filterable browsing. Runs as a single Docker container with an embedded database.

## Features

- **Library management** — Organize folders into libraries (Movies, TV, etc.). A folder can belong to multiple libraries and a library may have multiple folders.
- **Media scanning** — Extracts codec, resolution, HDR format, bitrate, audio tracks, subtitle tracks, and more using libmediainfo.
- **Filterable table** — Filter by codec, HDR type, audio language, channel layout, track counts, and many other fields.
- **Sortable columns** — Click any column header to sort. Supports sorting by track-level fields (video bitrate, audio codec, etc.).
- **Customizable columns** — Show/hide columns via a picker. Columns are grouped (General, Video, Audio, Subtitles) and can be resized and reordered.
- **Search** — Filter files by filename with instant search.
- **Scan queue** — Background queue processes files with priority support and subfolder-level prioritization.
- **Scan logs** — View history of all scan jobs with per-job file listings.
- **Scan progress** — Banner shows import progress while files are being scanned.
- **Automatic re-scans** — Configurable interval for detecting new/changed files (mtime-based).
- **Single container** — One `docker compose up` runs PostgreSQL, the backend, and nginx in a single container.

<img width="3839" height="2016" alt="image" src="https://github.com/user-attachments/assets/6a662768-fe82-4154-ad6b-3b27e2efbdc9" />

## Quick Start

1. Create a directory and add the two files below:

**docker-compose.yml:**
```yaml
services:
  mediainfodb:
    container_name: mediainfodb
    image: ghcr.io/admiralsparrow/mediainfodb:latest
    restart: unless-stopped
    volumes:
      - ${MOVIES:-/media}:/media/movies:ro
      - ${TV:-/media}:/media/tv:ro
      - ${DB_DATA_PATH:-mediainfodb-data}:/var/lib/postgresql/data
    environment:
      DATABASE_URL: ${DATABASE_URL:-}
      DB_PASSWORD: ${DB_PASSWORD:-mediainfo_dev}
      POSTGRES_DB: ${POSTGRES_DB:-mediainfodb}
      POSTGRES_USER: ${POSTGRES_USER:-mediainfodb}
      ALLOWED_BROWSE_ROOTS: ${ALLOWED_BROWSE_ROOTS:-/media}
      SCAN_INTERVAL_MINUTES: ${SCAN_INTERVAL_MINUTES:-360}
    ports:
      - "3745:3745"
    mem_limit: 2g
    cpus: 2.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3745/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

**.env:**
```env
# Media paths (mounted read-only into the container)
MOVIES=/path/to/your/movies
TV=/path/to/your/tv-shows

# Database
DB_PASSWORD=mediainfo_dev
DB_DATA_PATH=mediainfodb-data
# DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/mediainfo  # uncomment for external DB

# Application
ALLOWED_BROWSE_ROOTS=/media
SCAN_INTERVAL_MINUTES=360
```

2. Start the container:
```bash
docker compose up -d
```

3. Open http://localhost:3745

4. Create a library, then add folders to it using the folder browser.

### Updating

```bash
docker compose pull
docker compose up -d
```

### Building from Source

If you want to build from source instead of using the pre-built image:
```bash
git clone https://github.com/admiralsparrow/MediaInfoDB.git
cd MediaInfoDB
docker compose up -d --build
```

## Configuration

All configuration is via environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MOVIES` | `/media` | Host path mounted as `/media/movies` (read-only) |
| `TV` | `/media` | Host path mounted as `/media/tv` (read-only) |
| `DATABASE_URL` | *(internal)* | External PostgreSQL URL. Omit to use the embedded database. |
| `DB_PASSWORD` | `mediainfo_dev` | Password for the embedded PostgreSQL instance |
| `DB_DATA_PATH` | `mediainfodb-data` | Path or named volume for PostgreSQL data persistence |
| `ALLOWED_BROWSE_ROOTS` | `/media` | Comma-separated paths the folder browser can access |
| `SCAN_INTERVAL_MINUTES` | `360` | Minutes between automatic re-scans |

To mount additional media paths, add volume entries to `docker-compose.yml`.

## Using an External Database

To use an existing PostgreSQL instance instead of the embedded one, set `DATABASE_URL` in your `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/mediainfo docker compose up --build
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Single Container (:3745)             │
│                                                   │
│  ┌──────────┐   ┌──────────┐   ┌─────────────┐  │
│  │  nginx   │──>│  FastAPI  │──>│ PostgreSQL  │  │
│  │  proxy   │   │  backend  │   │   16 (embed)│  │
│  └──────────┘   └──────────┘   └─────────────┘  │
│       │              │                            │
│       │              ▼                            │
│       │       /media (read-only)                  │
│       ▼                                           │
│  Static frontend                                  │
│  (React/Vite build)                               │
└─────────────────────────────────────────────────┘
```

- **Frontend** — React 18, TypeScript, Vite, TanStack Query. Built at image build time and served as static files by nginx, which also proxies `/api` to the backend.
- **Backend** — Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic migrations, APScheduler for recurring scans.
- **Scanner** — Uses pymediainfo (libmediainfo) to extract codec, bitrate, HDR metadata, channel layouts, Atmos detection, hybrid remux flags, and more.
- **Database** — PostgreSQL 16, embedded in the container by default. Optionally point to an external instance via `DATABASE_URL`.

## Extracted Media Fields

| Category | Fields |
|----------|--------|
| General | Container format, title, overall bitrate, duration, file size, release group, source, provider, year, stream count, hybrid flag |
| Video | Codec, resolution, framerate, bitrate, bit depth, HDR10, HDR10+, Dolby Vision (profile/layer), aspect ratio, color primaries, transfer characteristics, encoding library, scan type, chroma subsampling, track name |
| Audio | Codec, bitrate, channels, channel layout (2.0/5.1/7.1.4), sample rate, compression mode, language, Atmos detection, commentary flag, original language flag, track name |
| Subtitles | Codec, language, hearing impaired flag, track name |

## Development

### Backend

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Creating a Migration

```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## API

The backend exposes a REST API under `/api/v1`. See [API.md](API.md) for full endpoint documentation, request/response schemas, and filter reference.


## Notice
This project does not use, and has no ties with MediaInfo by MediaArena.

## License

MIT
