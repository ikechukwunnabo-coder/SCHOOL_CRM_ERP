# Technology Compatibility Matrix

**Status:** In-progress scaffold validation (local). D-010 remains **provisional** pending CI and PostgreSQL/Redis runtime verification.

> Per Master Spec: verify official compatibility and security support, pin exact compatible versions, commit lockfiles. Do not blindly install unpinned latest versions.

## 1. Resolved / Observed (Scaffold) vs Targets

| Component | Target (D-010 baseline) | Resolved / Observed (this environment) | Evidence / Notes | Status |
|---|---|---|---|---|
| Python | 3.14.x | 3.14.7 (`python`/`py -3.14`) | Local venv `school_erp_venv/`; `manage.py check` and tests executed | **Observed locally** |
| Django | 5.2.x LTS | 5.2.19 | `backend/requirements.txt` (pip freeze, 69 pkgs) | **Pinned snapshot** |
| Django REST Framework | current stable compatible w/ Django 5.2 | 3.18.3 | `backend/requirements.txt`; auth/health API implemented | **Pinned snapshot** |
| drf-spectacular | current stable | 0.30.0 | `backend/requirements.txt`; schema/docs routes wired | **Pinned snapshot** |
| PostgreSQL | 18 (compose target) | 18 image configured (`docker-compose.yml`) | **Not runtime-validated** (Docker daemon unavailable in this env) | **Pending runtime verification** |
| psycopg | 3.2+ (binary ok for dev) | 3.3.9 + psycopg-binary 3.3.9 | Installed in venv and frozen; DB checks run via sqlite override | **Pinned, Postgres runtime pending** |
| Redis | 8 (compose target) | 8 image configured; redis-py 8.1.0 | **Not runtime-validated** | **Pending runtime verification** |
| Celery | 5.7+/compatible | 5.7.0 | `backend/requirements.txt`; app wiring present, broker runtime not validated | **Pinned, runtime pending** |
| Gunicorn | latest stable compatible | 27.0.1 | Installed/frozen; container/prod serving not validated | **Pinned snapshot** |
| Node.js | 22.x LTS target (CI) / local toolchain | v26.7.0 detected locally | `frontend/package-lock.json` present; build passed locally | **Observed locally (differs from CI target)** |
| npm | compatible | 12.0.2 detected (earlier) | Lockfile committed | **Observed locally** |
| React | 19.x | ^19.2.4 (`frontend/package.json`) | `npm run build` passed | **Lockfile-backed** |
| TypeScript | 5+/6 toolchain (scaffold) | ~6.0.2 (`frontend/package.json`) | `tsc -b` build passed | **Lockfile-backed** |
| Vite | 8.x (scaffold) | ^8.0.4 (`frontend/package.json`) | production build passed | **Lockfile-backed** |
| React Router | 7.x | ^7.6.0 (`frontend/package.json`) | auth routing shell implemented | **Lockfile-backed** |
| Docker / Compose | Engine + Compose v2 | Docker 29.9.2, Compose v5.6.1 detected | `docker compose up -d db redis` failed: daemon not running in this env | **Tooling present, runtime blocked** |

## 2. Local Scaffold Validation Evidence (2026-11-19)
- **Backend (sqlite override for local validation):** `ruff check apps config` pass; `python manage.py check` pass; `python manage.py makemigrations --check --dry-run` pass (no pending changes; initial migrations present for accounts/institutions/app_permissions/audit); `pytest -q` pass (**7 passed**: health endpoint, CSRF/login/me/logout flow, auth audit events, RBAC helpers/permission classes).
- **Frontend:** `npm install` completed, `frontend/package-lock.json` committed, `npm run build` (`tsc -b && vite build`) pass.
- **Dependencies/locks:** `backend/requirements.txt` and `backend/requirements-dev.txt` generated from venv (pip freeze). `frontend/package-lock.json` committed. `uv`/`pnpm` not available in environment.
- **Not validated:** Docker daemon unavailable, so Postgres/Redis-backed `manage.py`/migrations/test runs, container builds, and compose integration were **not** executed locally.

## 3. Package & Lockfile Strategy (current)
- **Backend:** declared in `backend/pyproject.toml`; pinned snapshot committed as `backend/requirements.txt` (+ `backend/requirements-dev.txt`) from scaffold venv. Future: consider compiled/hashed locks and CI drift checks.
- **Frontend:** `frontend/package.json` + committed `frontend/package-lock.json` (npm). CI configured for npm cache/install.
- **Python venv:** local `school_erp_venv/` at project root; not committed.
- **CI:** workflow scaffold added (`.github/workflows/ci.yml`) to install from pinned files and run lint/check/migration-check/tests (backend) and build/test (frontend); requires successful remote run for verification.

## 4. Compatibility Verification Checklist (D-010)
- [x] Generate backend dependency pin snapshot and frontend lockfile for scaffold
- [x] Run `django check`, migration consistency check, and backend test harness locally (sqlite override)
- [x] Run frontend typecheck/build locally
- [ ] Confirm Django 5.2 LTS support matrix for Python 3.14.x and selected PostgreSQL/psycopg in CI/official docs
- [ ] Confirm DRF, Celery, Redis client, auth/storage libs compatibility in integrated runtime (Postgres/Redis)
- [ ] Validate `docker compose` services (db/redis/backend/celery/frontend) and containerized workflows
- [ ] Achieve green CI run on pinned artifacts
- [ ] Review security support/EOL dates and harden pins as needed

## 5. Risks
- Python 3.14.x + Django 5.2 LTS/Postgres stack compatibility must be confirmed by authoritative docs and CI (D-010 remains provisional despite local scaffold success).
- Local validations used sqlite override because Docker/Postgres runtime was unavailable; Postgres-specific behavior/migrations/performance not yet verified.
- Local Node (26.x) differs from CI target (22.x); align supported Node LTS and verify frontend toolchain in CI.
- Provider SDKs (payments/SMS/email/storage) may introduce additional constraints when integrated.

**Decision status:** D-010 **Provisional — scaffold pinned/locally validated in part; pending CI and Postgres/Redis runtime verification.**
