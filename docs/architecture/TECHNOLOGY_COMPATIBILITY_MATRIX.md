# Technology Compatibility Matrix

**Status:** Validated locally through the M3/M4 acceptance-gap closure (2026-11-23): PostgreSQL 18 container healthy, 68 backend tests passing, audit-chain verification valid, frontend lint/unit/build/E2E green. Historical remote CI was green through the transcript slice (`45149166162`); the closure code is uncommitted/unpushed, so remote CI evidence is pending and no closure run ID exists. D-010 confirmed for committed pins.

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

## 2. Validation Evidence (2026-11-23)
- **Backend on PostgreSQL 18:** `ruff check apps config` pass; `python manage.py check` pass; `python manage.py makemigrations --check --dry-run` pass; `pytest -q` pass (**68 passed**). Historical slices were 29 M3 tests, 5 M4 examinations tests and 5 transcript tests; the closure adds object-level scoping, role/negative and cross-scope/IDOR tests, immutable audit-chain tests, PDF report cards, grading policy, timetable/teacher-attendance and alumni coverage.
- **Audit chain:** `python manage.py verify_audit_chain` -> valid (sequence, predecessor hash, entry hash).
- **Migrations:** `python manage.py makemigrations --check --dry-run` reports no drift; applied migrations include M3 workload/recurrence/publish and teacher attendance, M4 report-card PDF/grading policy, alumni linkage, role normalization and audit immutability chains.
- **Containers:** `docker compose up -d db redis` healthy (Postgres 18.7, Redis 8). Native Windows PostgreSQL on host port 5432 shadows the published port; use the compose network with `DOCKER_API_VERSION=1.44` for container-side validation.
- **Frontend:** `npm run lint` pass; `npm test` -> **17 Vitest tests passed**; `npm run build` (`tsc -b && vite build`) pass; `npm run test:e2e` -> **2 mocked Playwright specs passed**.
- **Remote CI:** historical runs green for scaffold (`44761962350`), Phase 2 (`44769870049`), Phase 2 closure (`44775171408`), M3 (`45130273958`, commit `d5c293a`), M4 examinations (`45135466158`, commit `3f04813`), M4 evidence (`45136374503`, commit `7913324`), and transcript (`45149166162`, commit `a603498`). CI now also runs backend audit-chain verification and frontend lint/E2E, but the closure code is not committed or pushed; there is no remote CI run ID for it and evidence is pending until commit/push.
- **Dependencies/locks:** `backend/requirements.txt` and `backend/requirements-dev.txt` pinned (pip freeze); `frontend/package-lock.json` committed. Deviation from the `uv`/`pnpm` target: neither tool is installed here, so pip freeze + npm lock are the committed locks.
- **Not validated:** backend Docker image export hangs in Docker Desktop; Celery worker and containerized backend runtime not exercised. M3/M4 are not accepted pending UAT/sign-off and Q-003.

## 3. Package & Lockfile Strategy (current)
- **Backend:** declared in `backend/pyproject.toml`; pinned snapshot committed as `backend/requirements.txt` (+ `backend/requirements-dev.txt`) from scaffold venv. Future: consider compiled/hashed locks and CI drift checks.
- **Frontend:** `frontend/package.json` + committed `frontend/package-lock.json` (npm). CI configured for npm cache/install.
- **Python venv:** local `school_erp_venv/` at project root; not committed.
- **CI:** workflow (`.github/workflows/ci.yml`) installs from pinned files and runs backend lint/check/migration-check/tests plus audit-chain verification, and frontend lint/unit tests/build/E2E. Local closure evidence is green; a successful remote run is still pending commit/push.

## 4. Compatibility Verification Checklist (D-010)
- [x] Generate backend dependency pin snapshot and frontend lockfile for scaffold
- [x] Run `django check`, migration consistency check, and backend test harness against PostgreSQL 18
- [x] Run frontend typecheck/build locally and in CI on Node 22
- [x] Run M3/M4 closure backend checks locally: 68 tests, audit-chain verification valid
- [x] Run M3/M4 closure frontend checks locally: lint, 17 Vitest tests, build, 2 mocked Playwright specs
- [ ] Obtain remote CI evidence for the closure (not committed/pushed; no run ID)
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

**Decision status:** D-010 **Validated for committed pins** (historical Phase 2/M3/M4/transcript CI green, PostgreSQL 18 runtime validated; M3/M4 closure locally validated with 68 backend tests, audit-chain verification, 17 Vitest tests and 2 mocked Playwright specs). Open follow-ups: remote CI evidence for the uncommitted closure, containerized backend/celery runtime, Celery/Redis integration, EOL review, and `uv`/`pnpm` lock tooling. M3/M4 remain not accepted pending UAT/sign-off and Q-003.
