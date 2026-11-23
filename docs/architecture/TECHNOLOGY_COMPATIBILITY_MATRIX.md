# Technology Compatibility Matrix

**Status:** Validated through the M4 transcript backend slice (2026-11-23): PostgreSQL 18 container healthy, 39 backend tests passing locally and in remote CI (`45149166162`); frontend build green. D-010 confirmed for committed pins.

> Per Master Spec: verify official compatibility and security support, pin exact compatible versions, commit lockfiles. Do not blindly install unpinned latest versions.

## 1. Resolved / Observed (Scaffold) vs Targets

| Component | Target (D-010 baseline) | Resolved / Observed (this environment) | Evidence / Notes | Status |
|---|---|---|---|---|
| Python | 3.14.x | 3.14.7 (`python`/`py -3.14`) | Local venv `school_erp_venv/`; `manage.py check` and tests executed | **Observed locally** |
| Django | 5.2.x LTS | 5.2.19 | `backend/requirements.txt` (pip freeze, 69 pkgs) | **Pinned snapshot** |
| Django REST Framework | current stable compatible w/ Django 5.2 | 3.18.3 | `backend/requirements.txt`; auth/health API implemented | **Pinned snapshot** |
| drf-spectacular | current stable | 0.30.0 | `backend/requirements.txt`; schema/docs routes wired | **Pinned snapshot** |
| PostgreSQL | 18 (compose target) | PostgreSQL 18.7 container (`school_erp_db`) healthy; tests ran on PostgreSQL 18 | Compose mount corrected to `/var/lib/postgresql` for 18+ image | **Runtime validated** |
| psycopg | 3.2+ (binary ok for dev) | 3.3.9 + psycopg-binary 3.3.9 | Installed in venv and frozen; DB checks run via sqlite override | **Pinned, Postgres runtime pending** |
| Redis | 8 (compose target) | Redis 8 container (`school_erp_redis`) healthy | `redis-cli ping` health check passing; backend cache operations not yet exercised by tests | **Container validated** |
| Celery | 5.7+/compatible | 5.7.0 | `backend/requirements.txt`; app wiring present, broker runtime not validated | **Pinned, runtime pending** |
| Gunicorn | latest stable compatible | 27.0.1 | Installed/frozen; container/prod serving not validated | **Pinned snapshot** |
| Node.js | 22.x LTS | v22 in CI and frontend Dockerfile; v26.7.0 observed locally | Remote CI build passed on Node 22 | **Aligned and CI-validated** |
| npm | compatible | 12.0.2 detected (earlier) | Lockfile committed | **Observed locally** |
| React | 19.x | ^19.2.4 (`frontend/package.json`) | `npm run build` passed | **Lockfile-backed** |
| TypeScript | 5+/6 toolchain (scaffold) | ~6.0.2 (`frontend/package.json`) | `tsc -b` build passed | **Lockfile-backed** |
| Vite | 8.x (scaffold) | ^8.0.4 (`frontend/package.json`) | production build passed | **Lockfile-backed** |
| React Router | 7.x | ^7.6.0 (`frontend/package.json`) | auth routing shell implemented | **Lockfile-backed** |
| Docker / Compose | Engine + Compose v2 | CLI 29.9.3 required `DOCKER_API_VERSION=1.44` for this Desktop engine | db/redis healthy; frontend image built; backend image export hangs in Docker Desktop | **Partial** |

## 2. Validation Evidence (2026-11-20)
- **Backend on PostgreSQL 18:** `ruff check apps config` pass; `python manage.py check` pass; `python manage.py makemigrations --check --dry-run` pass; `pytest -q` pass (**39 passed**: 29 at M3 covering health, auth/audit, RBAC/per-verb grants, institution/campus scoping, admissions, duplicate identity, guardians, lifecycle, private documents, imports, academic structure, teacher allocations, timetable conflicts, attendance scope/corrections; 5 M4 examinations covering assessment configuration, weighted scoring/grading, result workflow, correction history, report-card snapshots, and approval/publication role checks; 5 transcript covering PDF/QR generation, completeness blocking, issuance/download permissions, public verification, correction versioning, and revocation).
- **Migrations:** `python manage.py migrate` applied M1/M2/M3/M4 migrations successfully, including `app_permissions.0006_seed_phase4_transcript_permissions` and `app_transcripts.0001_initial`; `makemigrations --check --dry-run` reports no drift.
- **Containers:** `docker compose up -d db redis` healthy (Postgres 18.7, Redis 8). Native Windows PostgreSQL on host port 5432 shadows the published port; use the compose network with `DOCKER_API_VERSION=1.44` for container-side validation.
- **Frontend:** `npm run build` (`tsc -b && vite build`) pass locally and in remote CI on Node 22.
- **Remote CI:** green for scaffold (`44761962350`), Phase 2 (`44769870049`), Phase 2 closure (`44775171408`), M3 (`45130273958`, commit `d5c293a`), M4 examinations (`45135466158`, commit `3f04813`), M4 evidence (`45136374503`, commit `7913324`), and transcript (`45149166162`, commit `a603498`) against pinned `backend/requirements.txt` and `frontend/package-lock.json`. Node 20 action deprecation warnings are non-blocking.
- **Dependencies/locks:** `backend/requirements.txt` and `backend/requirements-dev.txt` pinned (pip freeze); `frontend/package-lock.json` committed. Deviation from the `uv`/`pnpm` target: neither tool is installed here, so pip freeze + npm lock are the committed locks.
- **Not validated:** backend Docker image export hangs in Docker Desktop; Celery worker and containerized backend runtime not exercised.

## 3. Package & Lockfile Strategy (current)
- **Backend:** declared in `backend/pyproject.toml`; pinned snapshot committed as `backend/requirements.txt` (+ `backend/requirements-dev.txt`) from scaffold venv. Future: consider compiled/hashed locks and CI drift checks.
- **Frontend:** `frontend/package.json` + committed `frontend/package-lock.json` (npm). CI configured for npm cache/install.
- **Python venv:** local `school_erp_venv/` at project root; not committed.
- **CI:** workflow scaffold added (`.github/workflows/ci.yml`) to install from pinned files and run lint/check/migration-check/tests (backend) and build/test (frontend); requires successful remote run for verification.

## 4. Compatibility Verification Checklist (D-010)
- [x] Generate backend dependency pin snapshot and frontend lockfile for scaffold
- [x] Run `django check`, migration consistency check, and backend test harness against PostgreSQL 18
- [x] Run frontend typecheck/build locally and in CI on Node 22
- [x] Confirm Django 5.2 LTS / Python 3.14 / psycopg 3 compatibility in the executed CI and local PostgreSQL 18 run
- [ ] Confirm DRF, Celery, Redis client, auth/storage libs compatibility in an integrated Celery/Redis runtime
- [ ] Validate `docker compose` backend/celery services and containerized workflows (db/redis and frontend image validated)
- [x] Achieve green CI runs on pinned artifacts (`44761962350`, `44769870049`, `44775171408`)
- [x] Achieve green CI run for the M3 commit after push (`45130273958`)
- [x] Achieve green CI run for the M4 examinations commit after push (`45135466158`)
- [x] Achieve green CI run for the transcript commit after push (`45149166162`)
- [ ] Review security support/EOL dates and harden pins as needed
- [ ] Replace pip freeze/npm locks with `uv.lock`/`pnpm-lock.yaml` when those tools are available (D-010 deviation)

## 5. Risks
- Docker Desktop image export hangs for the backend image; containerized backend/celery runtime remains unverified.
- A native Windows PostgreSQL on host port 5432 shadows the compose-published port; container-side validation must use the compose network.
- Lockfile tooling deviates from the approved `uv`/`pnpm` strategy (pip freeze and npm lock committed instead).
- Provider SDKs (payments/SMS/email/storage) may introduce additional constraints when integrated.

**Decision status:** D-010 **Validated for committed pins** (Phase 2/closure/M3/M4/transcript CI green, PostgreSQL 18 runtime validated, 39 backend tests locally and in CI through transcript slice). Open follow-ups: containerized backend/celery runtime, Celery/Redis integration, EOL review, and `uv`/`pnpm` lock tooling.
