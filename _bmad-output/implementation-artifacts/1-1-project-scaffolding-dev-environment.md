---
baseline_commit: 1dc3933fe26c6e430c6674907e473e2815019b28
---

# Story 1.1: Project Scaffolding & Dev Environment

Status: done

## Story

As a developer,
I want a working local dev environment with Docker Compose (PostgreSQL, Redis, FastAPI, React, MinIO), base DB schema (users, decks, ingest_jobs, audit_log tables), and a health-check API endpoint,
so that all subsequent stories have a running foundation to build on.

## Acceptance Criteria

1. **Given** a fresh clone of the repository, **When** I run `docker-compose up`, **Then** PostgreSQL, Redis, FastAPI, React dev server, and MinIO containers start successfully.
2. **Given** all containers are running, **When** I call `GET /api/v1/health`, **Then** it returns HTTP 200 with a JSON body containing service status for each dependency (postgres, redis, minio).
3. **Given** all containers are running, **When** I inspect the database, **Then** the DB contains `users`, `decks`, `ingest_jobs`, and `audit_log` tables per the architecture schema (Section 4).
4. **Given** all containers are running, **When** I open the React app in a browser, **Then** it renders a shell with a progress rail component showing placeholder steps (Ingest, Questions, Narratives, Verify, Render).

## Tasks / Subtasks

- [x] Task 1: Docker Compose setup (AC: #1)
  - [x] 1.1 Create `docker-compose.yml` with services: `postgres:15`, `redis:7`, `backend` (Python 3.11 FastAPI), `frontend` (Node 18 React dev server), `minio` (S3 mock)
  - [x] 1.2 Create `backend/Dockerfile` — Python 3.11 slim, install dependencies, run uvicorn
  - [x] 1.3 Create `frontend/Dockerfile` — Node 18, install deps, run dev server with hot reload
  - [x] 1.4 Configure networking so all services can communicate (shared docker network)
  - [x] 1.5 Add environment variables file (`.env.example`) with defaults for all services
  - [x] 1.6 Add volume mounts for postgres data persistence and minio storage

- [x] Task 2: FastAPI backend bootstrap (AC: #2)
  - [x] 2.1 Initialize FastAPI project structure under `backend/`
  - [x] 2.2 Create `backend/app/main.py` with FastAPI app instance, CORS middleware
  - [x] 2.3 Create `backend/app/api/v1/router.py` — versioned API router
  - [x] 2.4 Implement `GET /api/v1/health` endpoint returning `{"status": "ok", "services": {"postgres": "up"|"down", "redis": "up"|"down", "minio": "up"|"down"}}`
  - [x] 2.5 Create `backend/app/core/config.py` — Pydantic Settings for DB URL, Redis URL, MinIO config
  - [x] 2.6 Create `backend/app/core/database.py` — SQLAlchemy async engine + session factory (PostgreSQL)
  - [x] 2.7 Create `backend/app/core/redis.py` — Redis connection pool
  - [x] 2.8 Create `backend/requirements.txt` with pinned versions

- [x] Task 3: Database schema (AC: #3)
  - [x] 3.1 Create `backend/app/models/` with SQLAlchemy models for: `users`, `decks`, `ingest_jobs`, `audit_log`
  - [x] 3.2 Create Alembic migration for initial schema
  - [x] 3.3 Add DB init script or startup event to run migrations on container start
  - [x] 3.4 Add PostgreSQL trigger on `audit_log` to prevent DELETE (immutability per NFR7)

- [x] Task 4: React frontend shell (AC: #4)
  - [x] 4.1 Initialize React project under `frontend/` using Vite (or Create React App)
  - [x] 4.2 Create `ProgressRail` component — left sidebar showing 5 pipeline steps with placeholder icons
  - [x] 4.3 Create basic app shell layout with progress rail and main content area
  - [x] 4.4 Add API proxy config to forward `/api/*` requests to backend container

- [x] Task 5: Integration verification
  - [x] 5.1 Write a smoke test script that: starts docker-compose, waits for health, curls `/api/v1/health`, checks DB tables exist, confirms React serves on expected port
  - [x] 5.2 Add `README.md` with setup instructions (`docker-compose up`, expected URLs, env vars)

## Dev Notes

### Technical Stack (MANDATORY — do not deviate)

- **Backend:** Python 3.11 + FastAPI (async)
- **Frontend:** React (NOT SvelteKit — React for all screens per epics doc)
- **Database:** PostgreSQL 15 with JSONB columns
- **Cache:** Redis 7
- **File Storage:** MinIO (S3-compatible mock for dev)
- **ORM:** SQLAlchemy (async) with Alembic for migrations
- **API prefix:** `/api/v1/` — all endpoints versioned

### Database Schema (from Architecture Section 4)

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  organization TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE decks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE ingest_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deck_id UUID REFERENCES decks NOT NULL,
  file_url TEXT,
  schema_json JSONB,
  quality_report JSONB,
  validated_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deck_id UUID REFERENCES decks NOT NULL,
  user_id UUID REFERENCES users NOT NULL,
  action VARCHAR(100),
  details JSONB,
  created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_decks_user ON decks(user_id);
CREATE INDEX idx_audit_log_deck ON audit_log(deck_id);
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
```

**Audit log immutability trigger (NFR7):**
```sql
CREATE OR REPLACE FUNCTION prevent_audit_delete()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'DELETE on audit_log is forbidden';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER no_audit_delete
  BEFORE DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION prevent_audit_delete();
```

### Directory Structure

```
project-root/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── api/
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── router.py
│       │       └── endpoints/
│       │           └── health.py
│       ├── core/
│       │   ├── config.py
│       │   ├── database.py
│       │   └── redis.py
│       └── models/
│           ├── __init__.py
│           ├── user.py
│           ├── deck.py
│           ├── ingest_job.py
│           └── audit_log.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   └── ProgressRail.tsx
│   │   └── layouts/
│   │       └── AppShell.tsx
│   └── vite.config.ts
└── README.md
```

### Progress Rail Component (UX-DR1)

The progress rail is a persistent left sidebar showing 5 pipeline steps. For this story, implement as placeholder with no routing logic:

- Steps: Ingest, Questions, Narratives, Verify, Render
- Visual: vertical list, each step shows label + status icon (all inactive/placeholder for now)
- Current step should be highlightable (prop-driven)
- Completed steps should show a checkmark icon
- Desktop only: 1280px+ viewport (NFR9)

### Health Check Endpoint

`GET /api/v1/health` must actually probe each dependency:
- **PostgreSQL:** Execute `SELECT 1` via SQLAlchemy
- **Redis:** Execute `PING` via redis-py
- **MinIO:** Check bucket listing via boto3/minio client

Return shape:
```json
{
  "status": "ok",
  "services": {
    "postgres": "up",
    "redis": "up",
    "minio": "up"
  }
}
```

If any service is down, return status `"degraded"` with that service marked `"down"`. Still return HTTP 200 (the health check reports status, doesn't fail).

### Docker Compose Service Configuration

| Service | Image | Port | Notes |
|---------|-------|------|-------|
| postgres | postgres:15 | 5432 | Volume for data persistence |
| redis | redis:7 | 6379 | No persistence needed for dev |
| backend | Custom (Python 3.11) | 8000 | Uvicorn, auto-reload in dev |
| frontend | Custom (Node 18) | 3000 | Vite dev server, hot reload |
| minio | minio/minio | 9000/9001 | API port 9000, console 9001 |

### Key Dependencies (backend/requirements.txt)

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy[asyncio]>=2.0.23
asyncpg>=0.29.0
alembic>=1.13.0
redis>=5.0.0
boto3>=1.34.0
pydantic-settings>=2.1.0
python-multipart>=0.0.6
```

### Anti-Patterns to Avoid

- Do NOT use SQLite — must be PostgreSQL from day one
- Do NOT skip Redis — it's needed for session state in later stories
- Do NOT use synchronous SQLAlchemy — must be async from the start
- Do NOT hardcode connection strings — use environment variables via Pydantic Settings
- Do NOT create tables beyond users, decks, ingest_jobs, audit_log — other tables (question_sessions, narratives, reconciliation_reports, deck_selections, deck_outputs) belong to later stories
- Do NOT implement any business logic beyond health check — this is scaffolding only
- Do NOT use SvelteKit — the architecture mentions it for static pages but the epics specify React for all screens

### Testing Requirements

- Write a basic smoke test that verifies:
  - `docker-compose up` brings all services online
  - `GET /api/v1/health` returns 200 with all services "up"
  - Database tables exist (query `information_schema.tables`)
  - React dev server responds on port 3000
- Use `pytest` for backend tests
- Health check endpoint should have a unit test with mocked dependencies

### Project Structure Notes

- All backend code under `backend/app/` — FastAPI app factory pattern
- All frontend code under `frontend/src/` — standard React + Vite structure
- Docker Compose at project root
- Alembic config at `backend/alembic.ini`, migrations in `backend/alembic/versions/`
- Environment config via `.env.example` (never commit `.env`)

### References

- [Source: _bmad-output/planning-artifacts/ARCHITECTURE-Technical-Design.md#Section 4 - Database Schema]
- [Source: _bmad-output/planning-artifacts/ARCHITECTURE-Technical-Design.md#Section 8.1 - Development Environment]
- [Source: _bmad-output/planning-artifacts/ARCHITECTURE-Technical-Design.md#Section 5 - API Design]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1]
- [Source: _bmad-output/planning-artifacts/ux-designs/ux-bmad101-2026-06-18/EXPERIENCE.md#Progress Rail]

### Review Findings

- [x] [Review][Patch] Synchronous boto3 blocks async event loop in health check — wrapped in asyncio.to_thread [health.py:31]
- [x] [Review][Patch] Synchronous subprocess.run blocks event loop during startup — replaced with asyncio.create_subprocess_exec [main.py:13]
- [x] [Review][Patch] MinIO healthcheck uses `mc` which is not in minio image — replaced with curl healthcheck [docker-compose.yml:40]
- [x] [Review][Patch] Audit log trigger allows UPDATE defeating immutability — added BEFORE UPDATE trigger [001_initial_schema.py]
- [x] [Review][Patch] Missing index on ingest_jobs.deck_id foreign key — added index [001_initial_schema.py]
- [x] [Review][Patch] Missing minio-down unit test — added test [test_health.py]
- [x] [Review][Defer] No auth on endpoints — deferred, later story scope
- [x] [Review][Defer] Hardcoded dev credentials as defaults — deferred, expected for MVP dev
- [x] [Review][Defer] No cascade behavior on FKs — deferred, later story decisions
- [x] [Review][Defer] No status column on IngestJob — deferred, belongs to Story 1.2
- [x] [Review][Defer] Resource cleanup on shutdown (engine.dispose, redis close) — deferred, not in AC scope

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

### Completion Notes List

- All 5 tasks completed: Docker Compose, FastAPI backend, DB schema with Alembic, React frontend shell, integration tests
- Health endpoint probes all 3 dependencies (Postgres, Redis, MinIO) and reports degraded status if any fail
- Alembic migration includes audit_log immutability trigger (NFR7)
- ProgressRail component implements UX-DR1 with prop-driven step status
- 3 unit tests pass: health all-up, postgres-down, redis-down scenarios
- Smoke test script covers all 4 acceptance criteria

### File List

- docker-compose.yml (NEW)
- .env.example (NEW)
- README.md (NEW)
- backend/Dockerfile (NEW)
- backend/requirements.txt (NEW)
- backend/alembic.ini (NEW)
- backend/pytest.ini (NEW)
- backend/alembic/env.py (NEW)
- backend/alembic/script.py.mako (NEW)
- backend/alembic/versions/001_initial_schema.py (NEW)
- backend/app/__init__.py (NEW)
- backend/app/main.py (NEW)
- backend/app/api/__init__.py (NEW)
- backend/app/api/v1/__init__.py (NEW)
- backend/app/api/v1/router.py (NEW)
- backend/app/api/v1/endpoints/__init__.py (NEW)
- backend/app/api/v1/endpoints/health.py (NEW)
- backend/app/core/__init__.py (NEW)
- backend/app/core/config.py (NEW)
- backend/app/core/database.py (NEW)
- backend/app/core/redis.py (NEW)
- backend/app/models/__init__.py (NEW)
- backend/app/models/user.py (NEW)
- backend/app/models/deck.py (NEW)
- backend/app/models/ingest_job.py (NEW)
- backend/app/models/audit_log.py (NEW)
- backend/tests/__init__.py (NEW)
- backend/tests/conftest.py (NEW)
- backend/tests/test_health.py (NEW)
- frontend/Dockerfile (NEW)
- frontend/package.json (NEW)
- frontend/tsconfig.json (NEW)
- frontend/vite.config.ts (NEW)
- frontend/index.html (NEW)
- frontend/src/main.tsx (NEW)
- frontend/src/App.tsx (NEW)
- frontend/src/components/ProgressRail.tsx (NEW)
- frontend/src/layouts/AppShell.tsx (NEW)
- scripts/smoke-test.sh (NEW)
