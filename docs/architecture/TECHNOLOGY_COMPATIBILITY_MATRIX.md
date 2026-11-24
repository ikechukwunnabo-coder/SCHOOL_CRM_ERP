# Technology Compatibility Matrix

**Status:** Validated locally and in remote CI through the M3/M4 acceptance-gap closure (2026-11-23): PostgreSQL 18 container healthy, 68 backend tests passing, audit-chain verification valid, frontend lint/unit/build/E2E green. Closure CI run `45218305149` passed at commit `a7cfb58`; initial run `45217310279` failed because CI skipped database migration before audit verification and was fixed. Containerized backend/Celery runtime and Celery/Redis integration validated locally on 2026-11-24 (D-033); no CI run ID is claimed for that uncommitted work. D-010 confirmed for committed pins, including the locally validated container runtime.

> Per Master Spec: verify official compatibility and security support, pin exact compatible versions, commit lockfiles. Do not blindly install unpinned latest versions.

## 1. Resolved / Observed (Scaffold) vs Targets

| Component | Target (D-010 baseline) | Resolved / Observed (this environment) | Evidence / Notes | Status |
|---|---|---|---|---|
| Python | 3.14.x | 3.14.7 (`python`/`py -3.14`) | Local venv `school_erp_venv/`; `manage.py check` and tests executed | **Observed locally** |
| Django | 5.2.x LTS | 5.2.19 | `backend/requirements.txt` (pip freeze, 69 pkgs) | **Pinned snapshot** |
| Django REST Framework | current stable compatible w/ Django 5.2 | 3.18.3 | `backend/requirements.txt`; auth/health API implemented | **Pinned snapshot** |
| drf-spectacular | current stable | 0.30.0 | `backend/requirements.txt`; schema/docs routes wired | **Pinned snapshot** |
| PostgreSQL | 18 (compose target) | PostgreSQL 18.7 container (`school_erp_db`) healthy; tests ran on PostgreSQL 18 | Compose mount corrected to `/var/lib/postgresql` for 18+ image | **Runtime validated** |
| psycopg | 3.2+ (binary ok for dev) | 3.3.9 + psycopg-binary 3.3.9 | Installed in venv and frozen; PostgreSQL 18 container healthy and health endpoint reports `database:ok` in local Compose runtime (D-033) | **Pinned, Postgres runtime validated locally** |
| Redis | 8 (compose target) | Redis 8 container (`school_erp_redis`) healthy | `redis-cli ping` health check passing; cache operations exercised via health endpoint and `verify_runtime` (`django_redis.cache.RedisCache` at `REDIS_URL`) | **Runtime validated locally (D-033)** |
| Celery | 5.7+/compatible | 5.7.0 | `backend/requirements.txt`; broker, result backend and `core.ping` execution validated in local Compose runtime (D-033) | **Runtime validated locally (D-033)** |
| Gunicorn | latest stable compatible | 27.0.1 | Installed/frozen; container/prod serving not validated | **Pinned snapshot** |
| Node.js | 22.x LTS | v22 in CI and frontend Dockerfile; v26.7.0 observed locally | Remote CI build passed on Node 22 | **Aligned and CI-validated** |
| npm | compatible | 12.0.2 detected (earlier) | Lockfile committed | **Observed locally** |
| React | 19.x | ^19.2.4 (`frontend/package.json`) | `npm run build` passed | **Lockfile-backed** |
| TypeScript | 5+/6 toolchain (scaffold) | ~6.0.2 (`frontend/package.json`) | `tsc -b` build passed | **Lockfile-backed** |
| Vite | 8.x (scaffold) | ^8.0.4 (`frontend/package.json`) | production build passed | **Lockfile-backed** |
| React Router | 7.x | ^7.6.0 (`frontend/package.json`) | auth routing shell implemented | **Lockfile-backed** |
| Docker / Compose | Engine + Compose v2 | CLI 29.9.3 required `DOCKER_API_VERSION=1.44` for this Desktop engine | db/redis healthy; frontend image built; backend image built directly and via Compose and `backend`/`celery`/`celery_beat` validated (D-033) | **Validated locally** |

## 2. Validation Evidence (2026-11-23)
- **Backend on PostgreSQL 18:** `ruff check apps config` pass; `python manage.py check` pass; `python manage.py makemigrations --check --dry-run` pass; `pytest -q` pass (**68 passed**). Historical slices were 29 M3 tests, 5 M4 examinations tests and 5 transcript tests; the closure adds object-level scoping, role/negative and cross-scope/IDOR tests, immutable audit-chain tests, PDF report cards, grading policy, timetable/teacher-attendance and alumni coverage.
- **Audit chain:** `python manage.py verify_audit_chain` -> valid (sequence, predecessor hash, entry hash).
- **Migrations:** `python manage.py makemigrations --check --dry-run` reports no drift; applied migrations include M3 workload/recurrence/publish and teacher attendance, M4 report-card PDF/grading policy, alumni linkage, role normalization and audit immutability chains.
- **Containers:** `docker compose up -d db redis` healthy (Postgres 18.7, Redis 8). Native Windows PostgreSQL on host port 5432 shadows the published port; use the compose network with `DOCKER_API_VERSION=1.44` for container-side validation. Backend image built directly (`docker build -t school_crm_erp-backend:runtime -f backend/Dockerfile backend`) and via `docker compose up -d --build backend celery celery_beat`; both succeeded. Running/healthy: `school_erp_backend` healthy, `school_erp_celery` healthy, `school_erp_celery_beat` up, `school_erp_db` healthy, `school_erp_redis` healthy.
- **Frontend:** `npm run lint` pass; `npm test` -> **17 Vitest tests passed**; `npm run build` (`tsc -b && vite build`) pass; `npm run test:e2e` -> **2 mocked Playwright specs passed**.
- **Remote CI:** historical runs green for scaffold (`44761962350`), Phase 2 (`44769870049`), Phase 2 closure (`44775171408`), M3 (`45130273958`, commit `d5c293a`), M4 examinations (`45135466158`, commit `3f04813`), M4 evidence (`45136374503`, commit `7913324`), and transcript (`45149166162`, commit `a603498`). CI now also runs backend audit-chain verification and frontend lint/E2E; closure commit `a7cfb58` passed run `45218305149` after the initial closure run `45217310279` failed because the service DB was not migrated before audit verification.
- **Dependencies/locks:** `backend/requirements.txt` and `backend/requirements-dev.txt` pinned (pip freeze); `frontend/package-lock.json` committed. Deviation from the `uv`/`pnpm` target: neither tool is installed here, so pip freeze + npm lock are the committed locks.
- **Runtime/Celery/Redis (local, D-033):** health endpoint returns `{"status":"ok","database":"ok","cache":"ok"}`. `python manage.py verify_runtime` checks database, Redis cache, Celery broker, result backend, and `core.ping` registration/execution and passed. A real Celery worker consumed and completed a dispatched `core.ping` task with result `{'status': 'ok'}`. Celery beat starts with `PersistentScheduler` and schedule file `/var/lib/celery/celerybeat-schedule` persisted in the `celerybeat_data` volume.
- **Runtime configuration (local, D-033):** the Docker entrypoint applies migrations, collects static files, then execs the command; Celery commands skip migrations/static. Compose sets `DJANGO_ENV=docker` so container DB config uses `POSTGRES_HOST=db` instead of host `.env` `DATABASE_URL=...localhost...`; Redis cache uses `REDIS_URL` with `django_redis.cache.RedisCache`. Worker uses `--pool=solo` because prefork hung in this Docker Desktop/WSL2 environment; solo pool is the validated local Compose setting. Local validation only; no CI run ID is claimed for this uncommitted work.
- **Remaining follow-ups:** production orchestration and sizing (including prefork tuning and monitoring), provider integrations, EOL review and lockfile tooling. Containerized backend/Celery runtime, backend image build/export and Celery/Redis integration are validated locally and are no longer open blockers (D-033). M3/M4 are accepted with formal UAT/sign-off recorded and Q-003 confirmed (D-032).

## 3. Package & Lockfile Strategy (current)
- **Backend:** declared in `backend/pyproject.toml`; pinned snapshot committed as `backend/requirements.txt` (+ `backend/requirements-dev.txt`) from scaffold venv. Future: consider compiled/hashed locks and CI drift checks.
- **Frontend:** `frontend/package.json` + committed `frontend/package-lock.json` (npm). CI configured for npm cache/install.
- **Python venv:** local `school_erp_venv/` at project root; not committed.
- **CI:** workflow (`.github/workflows/ci.yml`) installs from pinned files and runs backend lint/check/migration-check/migrate/tests plus audit-chain verification, and frontend lint/unit tests/build/E2E. Local and remote closure evidence are green (`45218305149`).

## 4. Compatibility Verification Checklist (D-010)
- [x] Generate backend dependency pin snapshot and frontend lockfile for scaffold
- [x] Run `django check`, migration consistency check, and backend test harness against PostgreSQL 18
- [x] Run frontend typecheck/build locally and in CI on Node 22
- [x] Run M3/M4 closure backend checks locally: 68 tests, audit-chain verification valid
- [x] Run M3/M4 closure frontend checks locally: lint, 17 Vitest tests, build, 2 mocked Playwright specs
- [x] Obtain remote CI evidence for the closure (`45218305149` at `a7cfb58`; initial `45217310279` failure fixed in `a7cfb58`)
- [x] Confirm Django 5.2 LTS / Python 3.14 / psycopg 3 compatibility in the executed CI and local PostgreSQL 18 run
- [x] Confirm DRF, Celery and Redis client compatibility in an integrated Celery/Redis runtime (`verify_runtime` and `core.ping` locally, D-033); provider SDKs remain separate production concerns
- [x] Validate `docker compose` backend/celery services and containerized workflows (backend image built directly and via Compose, services healthy, D-033; db/redis and frontend image also validated)
- [x] Achieve green CI runs on pinned artifacts (`44761962350`, `44769870049`, `44775171408`)
- [x] Achieve green CI run for the M3 commit after push (`45130273958`)
- [x] Achieve green CI run for the M4 examinations commit after push (`45135466158`)
- [x] Achieve green CI run for the transcript commit after push (`45149166162`)
- [ ] Review security support/EOL dates and harden pins as needed
- [ ] Replace pip freeze/npm locks with `uv.lock`/`pnpm-lock.yaml` when those tools are available (D-010 deviation)

## 5. Risks
- `--pool=solo` is the validated local Compose setting because Celery prefork hung in this Docker Desktop/WSL2 environment; production prefork tuning remains a production-sizing item (D-033).
- A native Windows PostgreSQL on host port 5432 shadows the compose-published port; container-side validation must use the compose network.
- Lockfile tooling deviates from the approved `uv`/`pnpm` strategy (pip freeze and npm lock committed instead).
- Provider SDKs (payments/SMS/email/storage) may introduce additional constraints when integrated.

**Decision status:** D-010 **Validated for committed pins** (historical Phase 2/M3/M4/transcript CI green, PostgreSQL 18 runtime validated; M3/M4 closure validated with 68 backend tests, audit-chain verification, 17 Vitest tests, 2 mocked Playwright specs, and remote CI run `45218305149`; containerized runtime and Celery/Redis integration validated locally on 2026-11-24 per D-033, with no CI run ID claimed for that uncommitted work). Open follow-ups: production orchestration/sizing, prefork tuning, monitoring, provider integrations, EOL review, and `uv`/`pnpm` lock tooling. M3/M4 are accepted with formal UAT/sign-off recorded and Q-003 confirmed (D-032); the local runtime validation is recorded in D-033 and is not a production-readiness claim.
