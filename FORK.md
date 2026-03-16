# Lightnovel Crawler Fork

**Description:** Self-hosted light novel scraping service with chapter watcher and auto-download.
**Status:** Active (Phases 0-4 complete, ready for deployment)
**Owner:** Roland
**Upstream:** [dipu-bd/lightnovel-crawler](https://github.com/dipu-bd/lightnovel-crawler)
**Fork:** [rolandng84/lightnovel-crawler](https://github.com/rolandng84/lightnovel-crawler) (branch: `dev`)
**Frontend Fork:** [rolandng84/lncrawl-web](https://github.com/rolandng84/lncrawl-web) (branch: `main`)

## What This Fork Adds

1. **NovelFire Crawler** (`sources/en/n/novelfire.py`) - Custom crawler for novelfire.net
2. **Chapter Watcher** - Track novels for new chapters with auto-download
3. **Tracked Novels UI** - Frontend page at `/tracked-novels` with check/pause/delete actions
4. **Self-Host Docker** - `Dockerfile.selfhost` + `docker-compose.yml` for Coolify deployment
5. **Retry Failed** - Re-process only failed chapters/volumes/images instead of replaying entire job (`POST /api/job/{id}/retry-failed`)
6. **NovelBin Fixes** - Browser fallback + 403 auto-recovery for novelbin.com/.net/.me with multi-selector title parsing
7. **Selenium Grid Sidecar** - Optional browser container for sites with anti-bot protection
8. **Env Var Overrides** - Environment variables always override `config.json` cached values (critical for Docker/Coolify)

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Fork and setup | Done |
| 1 | Custom crawlers (NovelFire) | Done |
| 2 | Web UI dashboard (upstream frontend) | Done |
| 3 | Chapter watcher service | Done |
| 4 | Docker/Coolify deployment | Done |
| 5 | Documentation | Done |

## Quick Start

```bash
# Local development
make install
make start          # Backend at http://localhost:8080

# Frontend dev
cd ../lncrawl-web
npm install
npm run dev         # Frontend at http://localhost:5173, proxies to backend

# Docker deployment
cp .env.example .env
docker compose up -d
```

## Key Files (Fork-Specific)

- `AGENTS.md` - Claude Code context (CLAUDE.md equivalent)
- `Dockerfile.selfhost` - Multi-stage build with frontend
- `docker-compose.yml` - Self-hosted deployment stack (app + PostgreSQL + Selenium Grid)
- `lncrawl/dao/tracked_novel.py` - TrackedNovel model
- `lncrawl/services/watcher.py` - Watcher service
- `lncrawl/server/api/watcher.py` - Watcher API endpoints
- `lncrawl/services/jobs/service.py` - `retry_failed()` method (recursive CTE to find failed descendants)
- `lncrawl/server/api/jobs.py` - `POST /{job_id}/retry-failed` endpoint
- `sources/en/n/novelfire.py` - NovelFire crawler
- `sources/en/n/novel-bin.py` - NovelBin.com/.me crawler (browser fallback)
- `sources/en/n/novel-bin.net.py` - NovelBin.net crawler (browser fallback)
