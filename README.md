# School CRM & ERP Platform

Integrated School CRM & ERP platform (modular monolith) for Nursery, Primary and Secondary institutions — Nigeria baseline (`en-NG`, `NGN`, `Africa/Lagos`), one institution with multi-campus, API-first.

**Authoritative spec:** `MASTER_CRM_ERP_SCHOOL_PROMPT.md`  
**Phase 0 docs:** `docs/architecture/` (decisions, architecture, ERD, RBAC, workflows, API, plans)  
**Decisions register:** `docs/architecture/DECISIONS_REGISTER.md` (Approved for Phase 1 foundation start, conditional)

> Status: **Phase 1 foundation in progress.** Documented/approved baselines exist; no feature is considered implemented or tested unless evidenced.

## Stack (provisional baseline, D-010 — validate in scaffold/CI)
- **Backend:** Python 3.14.x, Django 5.2 LTS, Django REST Framework, PostgreSQL 18, Redis 8, Celery, Gunicorn
- **Frontend:** React 19, TypeScript, Vite, React Router
- **Infra:** Docker / Docker Compose, env-based config

## Repository layout
- `backend/` — Django + DRF application (`config/`, `apps/core|institutions|accounts|permissions|audit`)
- `frontend/` — React + TypeScript (Vite) auth/dashboard shell
- `infrastructure/` — deployment/infra assets
- `docs/architecture/` — Phase 0/Phase 1 architecture & readiness docs
- `scripts/`, `tests/` — helper and cross-cutting test assets
- `docker-compose.yml`, `.env.example`, `.github/workflows/ci.yml`

## Prerequisites
- Python 3.14.x, Node.js/npm, Docker & Docker Compose, PostgreSQL/Redis (local or via Docker)
- Local venv (recommended): `school_erp_venv/` at project root (not committed)

## Quick start (local)
1. Copy env: `Copy-Item .env.example .env` and adjust values.
2. Start services (when Docker daemon available): `docker compose up -d db redis` (optionally `backend`, `frontend`, `celery`).
3. Backend:
   - `py -3.14 -m venv school_erp_venv` (if needed), activate, `pip install -r backend/requirements.txt`
   - run migrations and server (from `backend/` or with `backend/manage.py`): `python manage.py migrate`, `python manage.py runserver`
4. Frontend: `cd frontend; npm install; npm run dev` (default Vite dev server).

## Local validation (current evidence)
- Backend: `ruff check apps config` pass; `python manage.py check` pass; `python manage.py makemigrations --check --dry-run` pass; `pytest -q` pass (7 tests: health, session/cookie auth flow, audit events, RBAC baseline helpers/permissions). Validated with `DATABASE_URL=sqlite:///...` in this environment.
- Frontend: `npm run build` pass (`tsc -b && vite build`); `frontend/package-lock.json` committed.
- Backend dependencies pinned via `backend/requirements.txt` and `backend/requirements-dev.txt` (pip freeze snapshot).
- **Not yet validated here:** Docker daemon was unavailable, so `docker compose` runtime, PostgreSQL/Redis service integration, and containerized CI-parity runs are pending.

## Current status
- **Documented/approved:** Phase 0 baselines and decisions (conditional; D-010 provisional). Q-001–Q-012 tracked (non-blocking for foundation).
- **Implemented (foundation, in progress):** env-driven Django/DRF config, custom `accounts.User` (UUID/email), institutions/campus models, permissions/RBAC models/helpers, audit model/middleware/service, session+CSRF auth endpoints (`/api/v1/auth/csrf|login|logout|me/`), health endpoint, initial migrations, basic frontend auth shell (login, protected dashboard, `/me` session restore), CI workflow scaffold.
- **Not complete:** full RBAC enforcement across domain APIs, comprehensive audit coverage/immutability hardening, Docker/Postgres runtime validation, production hardening, and Phase 2+ domain modules.

## Governance
Per `MASTER_CRM_ERP_SCHOOL_PROMPT.md` and `DECISIONS_REGISTER.md`: no hardcoded institution rules, backend-authoritative RBAC, audited sensitive actions, preserve historical/official records. A documented decision is not an implemented/tested system.
