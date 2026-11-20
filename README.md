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
- Backend: `ruff check apps config` pass; `python manage.py check` pass; `python manage.py makemigrations --check --dry-run` pass; `pytest -q` pass (**15 tests**: health, auth flow/audit, RBAC helpers and object scopes, institution/campus API cross-scope denial, audit redaction). Validated against PostgreSQL 18.
- Frontend: `npm run build` pass (`tsc -b && vite build`); `frontend/package-lock.json` committed.
- Backend dependencies pinned via `backend/requirements.txt` and `backend/requirements-dev.txt` (pip freeze snapshot).
- Remote CI green (run `44761962350`) on the pinned artifacts.
- **Not yet validated here:** containerized backend/Celery runtime (Docker Desktop stalls at image export) and Celery/Redis task integration.

## Current status
- **Documented/approved:** Phase 0 baselines, D-010 validated, RBAC matrix approved as the MVP authorization baseline (D-026), and Phase 2 approved to proceed. Q-001–Q-012 tracked (non-blocking for foundation).
- **Implemented (foundation, in progress):** env-driven Django/DRF config, custom `accounts.User` (UUID/email), institutions/campus models, permissions/RBAC models/helpers, audit model/middleware/service (redaction, scope derivation, denial logging), session+CSRF auth endpoints (`/api/v1/auth/csrf|login|logout|me/`), institution/campus-scoped read APIs (`/api/v1/institutions/`, `/api/v1/campuses/`) with deny-by-default RBAC, health endpoint, initial migrations, basic frontend auth shell (login, protected dashboard, `/me` session restore), CI workflow.
- **Not complete:** per-module per-verb role grants and enforcement in future domain APIs, database-level audit immutability, containerized backend/Celery runtime validation, production hardening, and Phase 2+ domain modules.

## Governance
Per `MASTER_CRM_ERP_SCHOOL_PROMPT.md` and `DECISIONS_REGISTER.md`: no hardcoded institution rules, backend-authoritative RBAC, audited sensitive actions, preserve historical/official records. A documented decision is not an implemented/tested system.
