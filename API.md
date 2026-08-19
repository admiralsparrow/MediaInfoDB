# API Documentation

Base URL: `/api/v1`

All endpoints are served by the FastAPI backend and proxied through nginx at port 3745 under the `/api/v1` prefix.

---

## Table of Contents

- [Browse](#browse)
- [Libraries](#libraries)
- [Folders](#folders)
- [Media](#media)
- [Queue](#queue)
- [Logs](#logs)
- [Status](#status)
- [Schemas](#schemas)
- [Filtering](#filtering)

---

## Browse

### GET `/api/v1/browse`

List filesystem directory contents. Returns allowed root directories when no path is specified.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string \| null | `null` | Directory path to list. Returns root drives/mounts if omitted. |

**Response:** `200 OK`

```json
[
  {
    "name": "Movies",
    "path": "/media/library1/Movies",
    "has_children": true
  }
]
```

**Errors:**

| Status | Detail |
|--------|--------|
| 403 | Path outside allowed roots |
| 404 | Directory not found |

---

## Libraries

### GET `/api/v1/libraries`

List all libraries with their associated folders and file counts.

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "name": "Movies",
    "created_at": "2024-01-15T10:30:00Z",
    "folders": [
      {
        "id": 1,
        "path": "/media/library1/Movies",
        "file_count": 542,
        "enabled": true
      }
    ]
  }
]
```

---

### POST `/api/v1/libraries`

Create a new library.

**Request Body:**

```json
{
  "name": "TV Shows"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Unique library name |

**Response:** `201 Created`

```json
{
  "id": 2,
  "name": "TV Shows",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Errors:**

| Status | Detail |
|--------|--------|
| 409 | Library name already exists |

---

### PATCH `/api/v1/libraries/{library_id}`

Update a library's name.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `library_id` | int | Library ID |

**Request Body:**

```json
{
  "name": "New Name"
}
```

**Response:** `200 OK` - Updated `LibraryResponse`

**Errors:**

| Status | Detail |
|--------|--------|
| 404 | Library not found |

---

### DELETE `/api/v1/libraries/{library_id}`

Delete a library. Folders that belong only to this library are also deleted.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `library_id` | int | Library ID |

**Response:** `204 No Content`

**Errors:**

| Status | Detail |
|--------|--------|
| 404 | Library not found |

---

## Folders

### GET `/api/v1/folders`

List all scanned folders with their library associations.

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "path": "/media/library1/Movies",
    "library_ids": [1],
    "added_at": "2024-01-15T10:30:00Z",
    "last_scanned": "2024-01-15T11:00:00Z",
    "scan_interval_minutes": 360,
    "enabled": true,
    "file_count": 542
  }
]
```

---

### POST `/api/v1/folders`

Add a new folder to scan. Triggers an immediate initial scan and schedules recurring scans.

**Request Body:**

```json
{
  "path": "/media/library1/TV",
  "library_ids": [2],
  "scan_interval_minutes": 360
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | yes | Absolute filesystem path to scan |
| `library_ids` | int[] | yes | At least one library ID to associate with |
| `scan_interval_minutes` | int \| null | no | Interval for automatic rescans. Null disables auto-rescan. |

**Response:** `201 Created` - `FolderResponse`

**Errors:**

| Status | Detail |
|--------|--------|
| 400 | One or more library IDs not found |
| 403 | Path outside allowed roots |
| 409 | Folder already added |

---

### DELETE `/api/v1/folders/{folder_id}`

Remove a folder and all its associated media files. Cancels scheduled scans.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `folder_id` | int | Folder ID |

**Response:** `204 No Content`

**Errors:**

| Status | Detail |
|--------|--------|
| 404 | Folder not found |

---

### PATCH `/api/v1/folders/{folder_id}`

Update folder settings.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `folder_id` | int | Folder ID |

**Request Body:**

```json
{
  "enabled": true,
  "scan_interval_minutes": 180,
  "library_ids": [1, 2]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | bool \| null | no | Enable/disable scanning |
| `scan_interval_minutes` | int \| null | no | New scan interval |
| `library_ids` | int[] \| null | no | Replace library associations |

**Response:** `200 OK` - `FolderResponse`

**Errors:**

| Status | Detail |
|--------|--------|
| 404 | Folder not found |

---

### DELETE `/api/v1/folders/{folder_id}/library/{library_id}`

Remove a folder from a specific library. If the folder has no remaining library associations, the folder and all its media files are deleted.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `folder_id` | int | Folder ID |
| `library_id` | int | Library ID to disassociate |

**Response:** `204 No Content`

**Errors:**

| Status | Detail |
|--------|--------|
| 404 | Folder not found |

---

### POST `/api/v1/folders/{folder_id}/rescan`

Trigger an immediate rescan of a folder.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `folder_id` | int | Folder ID |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force` | bool | `false` | When true, rescans all files regardless of mtime changes |

**Response:** `202 Accepted`

```json
{
  "message": "Scan triggered"
}
```

**Errors:**

| Status | Detail |
|--------|--------|
| 404 | Folder not found |

---

## Media

### GET `/api/v1/media`

List media files with pagination, sorting, and dynamic filtering. Returns full track details for each file.

**Pagination & Sort Parameters:**

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `page` | int | `1` | >= 1 | Page number |
| `page_size` | int | `50` | 1-10000 | Items per page |
| `sort` | string | `"file_name"` | See sort values below | Sort field |
| `order` | string | `"asc"` | `asc` or `desc` | Sort direction |

**Valid sort values:**

| Value | Description |
|-------|-------------|
| `file_name` | File name (alphabetical) |
| `title` | Media title |
| `container_format` | Container format (MKV, MP4, etc.) |
| `overall_bitrate` | Overall bitrate |
| `duration_ms` | Duration |
| `file_size_bytes` | File size |
| `relative_path` | Relative path within folder |
| `release_group` | Release group |
| `source` | Source tag |
| `provider` | Provider |
| `year` | Year |
| `stream_count` | Total stream count |
| `hybrid` | Hybrid remux flag |
| `scanned_at` | Scan timestamp |
| `file_modified_at` | File modification timestamp |
| `video_codec` | Video codec (MIN across tracks) |
| `video_bitrate` | Video bitrate (MAX across tracks) |
| `video_width` | Video width (MAX across tracks) |
| `video_height` | Video height (MAX across tracks) |
| `video_framerate` | Framerate (MAX across tracks) |
| `video_bit_depth` | Video bit depth (MAX across tracks) |
| `video_aspect_ratio` | Display aspect ratio (MIN across tracks) |
| `video_resolution` | Resolution label (MIN across tracks) |
| `audio_codec` | Audio codec (MIN across tracks) |
| `audio_bitrate` | Audio bitrate (MAX across tracks) |
| `audio_channels` | Audio channels (MAX across tracks) |
| `audio_sample_rate` | Audio sample rate (MAX across tracks) |

**Filter Parameters:**

See the [Filtering](#filtering) section below for full filter documentation.

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "file_path": "/media/library1/Movies/Movie.mkv",
    "file_name": "Movie.mkv",
    "relative_path": "Movies/Movie.mkv",
    "file_size_bytes": 15000000000,
    "container_format": "Matroska",
    "title": "Movie Title",
    "overall_bitrate": 25000000,
    "duration_ms": 7200000,
    "release_group": "GROUP",
    "source": "Blu-ray",
    "provider": null,
    "year": 2023,
    "stream_count": 8,
    "hybrid": false,
    "scanned_at": "2024-01-15T11:00:00Z",
    "file_modified_at": "2024-01-10T08:22:00Z",
    "video_tracks": [...],
    "audio_tracks": [...],
    "subtitle_tracks": [...]
  }
]
```

---

### GET `/api/v1/media/count`

Return the total count of media files matching the given filters. Accepts the same filter parameters as `GET /media`.

**Query Parameters:** Same filter parameters as `GET /api/v1/media` (pagination and sort params are ignored).

**Response:** `200 OK`

```json
{
  "count": 1523
}
```

---

### GET `/api/v1/media/filters/options`

Get available values for filter dropdowns. Only returns options for enum-type filters that have data in the database.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `library_id` | int \| null | `null` | Scope options to a specific library |

**Response:** `200 OK`

```json
{
  "container_format": ["Matroska", "MPEG-4"],
  "video.codec": ["HEVC", "AVC", "AV1"],
  "video.resolution": ["2160p", "1080p", "720p"],
  "audio.codec": ["AAC", "AC-3", "E-AC-3", "TrueHD"],
  "audio.channel_layout": ["2.0", "5.1", "7.1", "7.1.4"],
  "audio.language": ["en", "es", "fr"],
  "subtitle.language": ["en", "es", "fr"],
  "folder_path": ["Movies/Action", "Movies/Comedy"]
}
```

---

### GET `/api/v1/media/folders/tree`

Get distinct subfolder paths for building a folder filter tree in the UI.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `library_id` | int \| null | `null` | Scope to a specific library |

**Response:** `200 OK`

```json
[
  "Movies",
  "Movies/Action",
  "Movies/Comedy",
  "TV Shows"
]
```

---

### POST `/api/v1/media/rescan`

Queue specific media files for re-scanning by their IDs.

**Request Body:**

```json
{
  "file_ids": [1, 2, 3, 4, 5]
}
```

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `file_ids` | int[] | yes | 1-5000 items | Media file IDs to rescan |

**Response:** `202 Accepted`

```json
{
  "message": "Rescan queued for 5 file(s)"
}
```

**Errors:**

| Status | Detail |
|--------|--------|
| 400 | No file IDs provided |
| 400 | Maximum 5000 files per request |
| 404 | No matching files found |

---

### GET `/api/v1/media/{media_id}`

Get full details for a single media file including all track information.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `media_id` | int | Media file ID |

**Response:** `200 OK` - `MediaFileDetailResponse` (same shape as list items)

**Errors:**

| Status | Detail |
|--------|--------|
| 404 | Media file not found |

---

## Queue

The queue manages scan work items. Files are enqueued during folder scans and processed by background workers.

### GET `/api/v1/queue`

List queue items with filtering and pagination.

**Query Parameters:**

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `folder_id` | int \| null | `null` | | Filter by folder |
| `status` | string | `"pending"` | | Filter by status (`pending`, `processing`, `completed`, `failed`) |
| `limit` | int | `100` | <= 1000 | Max items to return |
| `offset` | int | `0` | | Pagination offset |

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "folder_id": 1,
    "file_path": "/media/library1/Movies/Movie.mkv",
    "relative_path": "Movies/Movie.mkv",
    "priority": 0,
    "status": "pending",
    "error_message": null
  }
]
```

---

### GET `/api/v1/queue/summary`

Get aggregated queue status counts grouped by folder.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder_id` | int \| null | `null` | Filter to a specific folder |

**Response:** `200 OK`

```json
[
  {
    "folder_id": 1,
    "folder_path": "/media/library1/Movies",
    "pending": 42,
    "processing": 2,
    "completed": 500,
    "failed": 3
  }
]
```

---

### GET `/api/v1/queue/subfolders`

Get subfolder tree with pending item counts for the prioritization UI.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `folder_id` | int | yes | Parent folder ID |

**Response:** `200 OK`

```json
[
  { "subfolder": "Action", "pending_count": 15 },
  { "subfolder": "Comedy", "pending_count": 8 },
  { "subfolder": "Drama", "pending_count": 3 }
]
```

Results are sorted by `pending_count` descending.

---

### PATCH `/api/v1/queue/{item_id}/priority`

Set the priority of a single queue item. Higher priority items are processed first.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `item_id` | int | Queue item ID |

**Request Body:**

```json
{
  "priority": 10
}
```

**Response:** `200 OK`

```json
{
  "ok": true
}
```

**Errors:**

| Status | Detail |
|--------|--------|
| 404 | Item not found |

---

### POST `/api/v1/queue/prioritize-subfolder`

Bulk-update priority for all pending items whose path starts with a given subfolder prefix.

**Request Body:**

```json
{
  "folder_id": 1,
  "prefix": "Action/",
  "priority": 10
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `folder_id` | int | yes | Parent folder ID |
| `prefix` | string | yes | Subfolder path prefix (trailing `/` is normalized) |
| `priority` | int | yes | New priority value for matching items |

**Response:** `200 OK`

```json
{
  "updated": 15
}
```

---

### DELETE `/api/v1/queue/completed`

Remove completed items from the queue.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder_id` | int \| null | `null` | Scope deletion to a specific folder |

**Response:** `200 OK`

```json
{
  "deleted": 500
}
```

---

### DELETE `/api/v1/queue/failed`

Remove failed items from the queue. These files will be retried on the next scan.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder_id` | int \| null | `null` | Scope deletion to a specific folder |

**Response:** `200 OK`

```json
{
  "deleted": 3
}
```

---

## Logs

### GET `/api/v1/logs`

List scan job history with filtering and pagination.

**Query Parameters:**

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `folder_id` | int \| null | `null` | | Filter by folder |
| `status` | string \| null | `null` | | Filter by job status |
| `limit` | int | `50` | 1-200 | Max items to return |
| `offset` | int | `0` | | Pagination offset |

**Response:** `200 OK`

```json
{
  "total": 150,
  "items": [
    {
      "id": 1,
      "folder_id": 1,
      "folder_path": "/media/movies/Action",
      "started_at": "2024-01-15T11:00:00",
      "finished_at": "2024-01-15T11:05:30",
      "status": "completed",
      "files_found": 542,
      "files_scanned": 542,
      "error_message": null
    }
  ]
}
```

---

### GET `/api/v1/logs/{job_id}/files`

Get the list of files that were scanned during a specific scan job.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | int | Scan job ID |

**Response:** `200 OK`

```json
{
  "files": [
    {
      "id": 42,
      "file_name": "Movie.mkv",
      "relative_path": "Action/Movie.mkv"
    }
  ]
}
```

---

## Status

### GET `/api/v1/health`

Health check endpoint. Verifies database connectivity.

**Response:** `200 OK`

```json
{
  "status": "healthy"
}
```

---

### GET `/api/v1/scans/active`

List currently running scan jobs with progress information.

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "folder_path": "/media/library1/Movies",
    "files_found": 542,
    "files_scanned": 128
  }
]
```

---

## Schemas

### VideoTrackResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Track database ID |
| `track_index` | int | Track index within the file |
| `codec` | string \| null | Video codec (HEVC, AVC, AV1, etc.) |
| `bitrate` | int \| null | Bitrate in bits/second |
| `width` | int \| null | Frame width in pixels |
| `height` | int \| null | Frame height in pixels |
| `framerate` | float \| null | Framerate (e.g. 23.976) |
| `hdr10` | bool | HDR10 flag |
| `dolby_vision` | bool | Dolby Vision flag |
| `dv_layer` | string \| null | Dolby Vision layer (BL, EL, etc.) |
| `dv_profile` | int \| null | Dolby Vision profile number |
| `hdr10_plus` | bool | HDR10+ flag |
| `language` | string \| null | Track language (ISO 639) |
| `track_name` | string \| null | Track title/name |
| `is_default` | bool | Default track flag |
| `is_forced` | bool | Forced track flag |
| `display_aspect_ratio` | string \| null | Display aspect ratio (e.g. "16:9") |
| `bit_depth` | int \| null | Bit depth (8, 10, 12) |
| `color_primaries` | string \| null | Color primaries (BT.709, BT.2020, etc.) |
| `transfer_characteristics` | string \| null | Transfer characteristics (PQ, HLG, etc.) |
| `encoding_library` | string \| null | Encoding library used |
| `scan_type` | string \| null | Scan type (Progressive, Interlaced) |
| `chroma_subsampling` | string \| null | Chroma subsampling (4:2:0, 4:2:2, etc.) |
| `resolution` | string \| null | Resolution label (2160p, 1080p, etc.) |

### AudioTrackResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Track database ID |
| `track_index` | int | Track index within the file |
| `codec` | string \| null | Audio codec (AAC, AC-3, TrueHD, etc.) |
| `bitrate` | int \| null | Bitrate in bits/second |
| `channel_layout` | string \| null | Channel layout (2.0, 5.1, 7.1.4, etc.) |
| `channels` | int \| null | Number of channels |
| `language` | string \| null | Track language (ISO 639) |
| `track_name` | string \| null | Track title/name |
| `is_default` | bool | Default track flag |
| `is_original` | bool | Original language flag |
| `is_forced` | bool | Forced track flag |
| `is_commentary` | bool | Commentary track flag |
| `is_atmos` | bool | Dolby Atmos detection |
| `sample_rate` | int \| null | Sample rate in Hz |
| `compression_mode` | string \| null | Compression mode (Lossy, Lossless) |

### SubtitleTrackResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Track database ID |
| `track_index` | int | Track index within the file |
| `codec` | string \| null | Subtitle codec (SRT, ASS, PGS, etc.) |
| `language` | string \| null | Track language (ISO 639) |
| `track_name` | string \| null | Track title/name |
| `is_default` | bool | Default track flag |
| `is_forced` | bool | Forced track flag |
| `is_hearing_impaired` | bool | Hearing impaired / SDH flag |

---

## Filtering

The media list endpoint (`GET /api/v1/media`) and count endpoint (`GET /api/v1/media/count`) support dynamic filtering via query parameters. Filters are applied as AND conditions.

### Filter Types

| Type | Behavior | Example |
|------|----------|---------|
| **enum** | Comma-separated values, matches any (SQL `IN`). Prefix with `!` to negate (files that do NOT match). | `video.codec=HEVC,AVC` or `video.codec=!HEVC` |
| **boolean** | `true`/`1`/`yes` = true, anything else = false | `video.hdr10=true` |
| **gte** | Greater than or equal (integer) | `video.bitrate_min=10000000` |
| **lte** | Less than or equal (integer) | `overall_bitrate_max=50000000` |
| **date_gte** | On or after date (ISO 8601 date string) | `scanned_at_min=2024-01-01` |
| **date_lte** | On or before date (inclusive, full day) | `file_modified_at_max=2024-06-30` |
| **count_gte** | Track count >= value (files with at least N tracks) | `audio.track_count_min=2` |
| **count_lte** | Track count <= value (files with at most N tracks) | `subtitle.track_count_max=5` |
| **text** | Case-insensitive substring match (SQL `ILIKE %val%`) | `search=avengers` |
| **prefix** | Path prefix match (SQL `LIKE val%`) | `folder_path=Movies/Action` |

### Available Filters

#### General

| Parameter | Type | Description |
|-----------|------|-------------|
| `library_id` | int | Filter by library (exact match via join) |
| `search` | text | Search in file name |
| `folder_path` | prefix | Filter by folder path prefix |
| `container_format` | enum | Container format (Matroska, MPEG-4, etc.) |
| `title` | text | Search in media title |
| `overall_bitrate_min` | gte | Minimum overall bitrate |
| `overall_bitrate_max` | lte | Maximum overall bitrate |
| `release_group` | enum | Release group |
| `source` | enum | Source tag |
| `provider` | enum | Provider |
| `year` | enum | Release year |
| `hybrid` | boolean | Hybrid remux flag |
| `scanned_at_min` | date_gte | Scanned on or after date |
| `scanned_at_max` | date_lte | Scanned on or before date |
| `file_modified_at_min` | date_gte | File modified on or after date |
| `file_modified_at_max` | date_lte | File modified on or before date |

#### Video Track Filters

| Parameter | Type | Description |
|-----------|------|-------------|
| `video.codec` | enum | Video codec |
| `video.bitrate_min` | gte | Minimum video bitrate |
| `video.bitrate_max` | lte | Maximum video bitrate |
| `video.width_min` | gte | Minimum video width |
| `video.width_max` | lte | Maximum video width |
| `video.height_min` | gte | Minimum video height |
| `video.height_max` | lte | Maximum video height |
| `video.resolution` | enum | Resolution label (2160p, 1080p, etc.) |
| `video.hdr10` | boolean | Has HDR10 |
| `video.dolby_vision` | boolean | Has Dolby Vision |
| `video.dv_profile` | enum | Dolby Vision profile |
| `video.dv_layer` | enum | Dolby Vision layer |
| `video.hdr10_plus` | boolean | Has HDR10+ |
| `video.language` | enum | Video track language |
| `video.is_default` | boolean | Is default track |
| `video.is_forced` | boolean | Is forced track |
| `video.display_aspect_ratio` | enum | Display aspect ratio |
| `video.bit_depth` | enum | Bit depth |
| `video.color_primaries` | enum | Color primaries |
| `video.transfer_characteristics` | enum | Transfer characteristics |
| `video.encoding_library` | enum | Encoding library |
| `video.scan_type` | enum | Scan type |
| `video.chroma_subsampling` | enum | Chroma subsampling |

#### Audio Track Filters

| Parameter | Type | Description |
|-----------|------|-------------|
| `audio.codec` | enum | Audio codec |
| `audio.bitrate_min` | gte | Minimum audio bitrate |
| `audio.bitrate_max` | lte | Maximum audio bitrate |
| `audio.channel_layout` | enum | Channel layout |
| `audio.language` | enum | Audio language |
| `audio.is_default` | boolean | Is default track |
| `audio.is_original` | boolean | Is original language |
| `audio.is_forced` | boolean | Is forced track |
| `audio.is_commentary` | boolean | Is commentary |
| `audio.is_atmos` | boolean | Has Dolby Atmos |
| `audio.sample_rate` | enum | Sample rate |
| `audio.compression_mode` | enum | Compression mode |
| `audio.track_count_min` | count_gte | Minimum number of audio tracks |
| `audio.track_count_max` | count_lte | Maximum number of audio tracks |

#### Subtitle Track Filters

| Parameter | Type | Description |
|-----------|------|-------------|
| `subtitle.codec` | enum | Subtitle codec |
| `subtitle.language` | enum | Subtitle language |
| `subtitle.is_default` | boolean | Is default track |
| `subtitle.is_forced` | boolean | Is forced track |
| `subtitle.is_hearing_impaired` | boolean | Is hearing impaired / SDH |
| `subtitle.track_count_min` | count_gte | Minimum number of subtitle tracks |
| `subtitle.track_count_max` | count_lte | Maximum number of subtitle tracks |

### Filter Examples

```bash
# 4K HDR10 movies in a specific library
GET /api/v1/media?library_id=1&video.resolution=2160p&video.hdr10=true

# Files with Dolby Atmos audio in English
GET /api/v1/media?audio.is_atmos=true&audio.language=en

# Search for a title, sorted by file size descending
GET /api/v1/media?search=batman&sort=file_size_bytes&order=desc

# HEVC or AV1 files with 10-bit depth
GET /api/v1/media?video.codec=HEVC,AV1&video.bit_depth=10

# Files in a specific subfolder with lossless audio
GET /api/v1/media?folder_path=Movies/Action&audio.compression_mode=Lossless

# Hybrid remux files
GET /api/v1/media?hybrid=true

# Files with at least 3 audio tracks
GET /api/v1/media?audio.track_count_min=3

# Files that do NOT have HEVC video (negated enum filter with ! prefix)
GET /api/v1/media?video.codec=!HEVC

# Files that do NOT have English or Spanish audio
GET /api/v1/media?audio.language=!en,es

# Files scanned in January 2024
GET /api/v1/media?scanned_at_min=2024-01-01&scanned_at_max=2024-01-31

# Files modified after a specific date
GET /api/v1/media?file_modified_at_min=2024-06-01
```
