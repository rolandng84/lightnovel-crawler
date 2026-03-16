# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Setup virtual environment and Install Python dependencies
make install

# Run development servers
make start         # Backend server only
make watch         # Backend with auto-reload

# Build
make build         # Full build (web + wheel + exe)
make build-wheel   # Python wheel only
make build-exe     # PyInstaller executable

# Linting
make lint          # Both Python and web
make lint-py       # Python (flake8)
make lint-web      # Web frontend (eslint)

# Dependencies (uv)
make add-dep httpx          # Add runtime dependency
make add-dev black          # Add dev dependency
make rm-dep httpx           # Remove runtime dependency
make rm-dev black           # Remove dev dependency

# Docker Commands
make docker-build       # Build application Docker image
make docker-up          # Start containers in background
make docker-down        # Stop containers
make docker-logs

# Run from source directly
uv run python -m lncrawl
```

## Architecture Overview

### Entry Point & Application Context

- **`lncrawl/__main__.py`**: Entry point, calls `main()` from `lncrawl.app`
- **`lncrawl/context.py`**: `AppContext` singleton manages all services via lazy-loaded properties
- **`lncrawl/app.py`**: CLI setup using Typer, registers subcommands (crawl, search, server, sources, config)

### Source Crawlers

**Location**: `sources/` - Organized by language (`en/`, `zh/`, `ja/`, etc.), English further split alphabetically

**Key Base Classes**:

- `lncrawl/core/crawler.py`: `Crawler` class - extend this to create new source crawlers
  - Required: `read_novel_info()`, `download_chapter_body()`
  - Optional: `initialize()`, `login()`, `search_novel()`
- `lncrawl/core/scraper.py`: `Scraper` base - HTTP requests, BeautifulSoup parsing, Cloudflare handling
- `lncrawl/core/taskman.py`: `TaskManager` - ThreadPoolExecutor for concurrent operations

**Crawler Registration**: `lncrawl/services/sources/service.py`

- Crawlers auto-discovered by importing Python files from source directories
- Each crawler has: `__id__`, `base_url`, `version` metadata
- Full-text search index for fast source lookup

### Server/API

**FastAPI Server**: `lncrawl/server/app.py`

- REST API at `/api`, frontend at `/`
- Endpoints in `lncrawl/server/api/`: novels, chapters, volumes, jobs, artifacts, auth, libraries, watcher

### Output Generation

**Binder Service**: `lncrawl/services/binder/`

- `epub.py`: Native EPUB generation (primary format)
- `calibre.py`: Converts EPUB to other formats (MOBI, PDF, DOCX, etc.) via Calibre
- `json.py`, `text.py`: JSON and plain text formats

### Data Models

- **`lncrawl/models/`**: Chapter, Volume, Novel, SearchResult, Session
- **`lncrawl/dao/`**: Database access objects (SQLAlchemy/SQLModel), includes TrackedNovel

### Services (via AppContext)

`lncrawl` is structured around a set of **services**, each responsible for a major piece of application functionality. All core services are accessed via the singleton `AppContext` (usually as `ctx` in code). This allows shared, on-demand initialization and simple dependency management throughout the app.

**Key services available from the app context:**

- **config**: Configuration manager (loads and saves user settings, environment variables, CLI flags)
- **db**: Database access (SQLModel, manages library, jobs, novels, chapters)
- **http**: HTTP client (handles web requests, session, caching, retries, Cloudflare support)
- **sources**: Source crawler registry/discovery (loads all available crawlers, search/index)
- **crawler**: The currently selected/active crawler instance (handles all scraping logic for a selected source)
- **binder**: Output/binding manager (handles EPUB generation, invoking Calibre for conversions, text export)
- **jobs**: Background job/task queue (for crawling, downloads, conversions)
- **novels**: Novel library management (add/remove novels, metadata)
- **chapters**: Chapters manager (fetch/save chapter data)
- **volumes**: Volumes manager (volume/chapter grouping, manipulation)
- **watcher**: Chapter watcher service (tracks novels for new chapters, auto-downloads)

All services are **lazily loaded** as properties of the context to optimize performance and resource use.

For command-line tools, FastAPI server endpoints, and crawlers, you should always access shared services via `ctx` for consistency and compatibility.

## Creating a New Source Crawler

**Full guide:** [.github/docs/CREATING_CRAWLERS.md](.github/docs/CREATING_CRAWLERS.md)

**Recommended:** Copy **`sources/_examples/_01_general_soup.py`** and use **`GeneralSoupTemplate`** (`lncrawl.templates.soup.general`). Implement:

- **Required:** `parse_title(soup)`, `parse_cover(soup)`, `parse_chapter_list(soup)` (yield `Chapter`/`Volume`), `select_chapter_body(soup)` (return the chapter text Tag).
- **Optional:** `parse_authors(soup)`, `parse_summary(soup)`, `get_novel_soup()`, `initialize()`, `login()`.

For search use `_02_searchable_soup.py` (SearchableSoupTemplate)

For volumes use `_05_with_volume_soup.py` or `_07_optional_volume_soup.py`

For JS-heavy sites use browser examples (`_09`–`_17`).

Alternative: base **`Crawler`** with `read_novel_info()` and `download_chapter_body()` via `_00_basic.py`.

Test: `uv run python -m lncrawl -s "URL" --first 3 -f` and `uv run python -m lncrawl sources list | grep mysite`.

## Chapter Watcher (Fork Addition)

The watcher service periodically checks tracked novels for new chapters and optionally auto-downloads them.

### Key Files

- **`lncrawl/dao/tracked_novel.py`**: TrackedNovel model (user_id, novel_url, check_interval, auto_download, etc.)
- **`lncrawl/services/watcher.py`**: WatcherService with CRUD + `check_novel()` + `run_check()` loop
- **`lncrawl/server/api/watcher.py`**: API endpoints at `/api/watcher/*`
- **`lncrawl/server/models/watcher.py`**: Request/response Pydantic models
- **Frontend**: `src/pages/TrackedNovels/` in the `lncrawl-web` repo

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchers` | List user's tracked novels |
| GET | `/api/watcher/all` | List all tracked novels |
| POST | `/api/watcher` | Track a novel |
| GET | `/api/watcher/{id}` | Get tracked novel |
| PATCH | `/api/watcher/{id}` | Update tracked novel |
| DELETE | `/api/watcher/{id}` | Stop tracking |
| POST | `/api/watcher/{id}/check` | Force check now |

### How It Works

1. Scheduler runs `run_check()` every 60 seconds (daemon thread)
2. For each active, non-complete tracked novel where `check_interval_minutes` has elapsed:
   - Calls `ctx.crawler.fetch_novel()` to get current chapter count
   - Compares with `last_known_chapters`
   - If new chapters found and `auto_download` is true, creates a download job
3. Errors are captured in `last_error` and `last_checked_at` is always updated

## Retry Failed (Fork Addition)

When a crawl job completes with partial failures (e.g., "Failed: 7%"), the "Retry Failed" button re-processes only the failed items instead of replaying the entire job.

### How It Works

1. `retry_failed()` in `lncrawl/services/jobs/service.py` uses the `select_descendends()` recursive CTE to find ALL failed descendant jobs
2. Groups failed jobs by type: `CHAPTER`, `IMAGE`, `VOLUME`
3. Creates appropriate batch jobs (`fetch_many_chapters`, `fetch_many_images`, `fetch_many_volumes`) with only the failed IDs
4. If multiple types failed, chains them with `depends_on`

### Key Files

- **`lncrawl/services/jobs/service.py`**: `retry_failed()` method
- **`lncrawl/server/api/jobs.py`**: `POST /{job_id}/retry-failed` endpoint
- **`lncrawl/exceptions.py`**: `ServerErrors.no_failed_items` error constant
- **Frontend**: "Retry Failed" button in `src/pages/JobDetails/JobActionButtons.tsx` (lncrawl-web)

### Job Hierarchy

```
FULL_NOVEL → VOLUME_BATCH → VOLUME → CHAPTER_BATCH → CHAPTER → IMAGE_BATCH → IMAGE
```

**Replay** creates a new parent job → re-downloads everything. **Retry Failed** finds leaf-level failures and creates targeted batch jobs.

## NovelBin Crawlers (Fork Addition)

Custom crawlers for novelbin sites that use Cloudflare protection.

### Key Files

- **`sources/en/n/novel-bin.py`**: Handles `novelbin.com` and `novelbin.me`
- **`sources/en/n/novel-bin.net.py`**: Handles `novel-bin.net`

### Anti-Bot Strategy

Both crawlers extend `GeneralBrowserTemplate` + `NovelFullTemplate`:
- `auto_refresh_on_403 = True` with `max_403_retries = 3`
- `visit_novel_page_in_browser()` waits for title elements with multiple CSS selectors
- Falls back to meta tags and `<title>` tag for title parsing
- Rate-limited to 1 request/second

## Self-Hosted Docker Deployment (Fork Addition)

### Files

- **`Dockerfile.selfhost`**: Multi-stage build (Node 22 frontend + upstream base image)
- **`docker-compose.yml`**: PostgreSQL + app + Selenium Grid with healthchecks and named volumes
- **`.env.example`**: Configuration template

### Services

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | `Dockerfile.selfhost` | Main app (FastAPI + frontend) |
| `postgres` | `postgres:17-alpine` | Database |
| `selenium` | `selenium/standalone-chromium` | Browser for anti-bot sites (novelbin, etc.) |

### Environment Variable Overrides

Env vars always override `config.json` cached values. Key vars for Docker/Coolify:
- `LNCRAWL_DATA_PATH` — Data storage path (default: `/data`)
- `DATABASE_URL` — PostgreSQL connection string
- `SELENIUM_GRID_URL` — Selenium Grid URL (e.g., `http://selenium:4444`)

### Quick Start

```bash
cp .env.example .env   # edit POSTGRES_PASSWORD
docker compose up -d
# Server at http://localhost:8080, login with admin/admin
```

### Build Args

| Arg | Default | Description |
|-----|---------|-------------|
| `FRONTEND_REPO` | `https://github.com/rolandng84/lncrawl-web.git` | Frontend source repo |
| `FRONTEND_BRANCH` | `main` | Frontend branch to build |
| `BASE_IMAGE` | `ghcr.io/lncrawl/lncrawl-base:latest` | Base image with Calibre + deps |
