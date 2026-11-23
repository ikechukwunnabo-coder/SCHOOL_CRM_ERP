# School CRM & ERP Platform

Integrated School CRM & ERP platform (modular monolith) for Nursery, Primary and Secondary institutions — Nigeria baseline (`en-NG`, `NGN`, `Africa/Lagos`), one institution with multi-campus, API-first.

**Authoritative spec:** `MASTER_CRM_ERP_SCHOOL_PROMPT.md`  
**Phase 0 docs:** `docs/architecture/` (decisions, architecture, ERD, RBAC, workflows, API, plans)  
**Decisions register:** `docs/architecture/DECISIONS_REGISTER.md` (Approved for Phase 1 foundation start, conditional)

> Status: **M3/M4 technical hardening gaps implemented locally; not accepted pending formal UAT/sign-off and Q-003 grading-policy confirmation.** Documented/approved baselines exist; no feature is considered implemented or tested unless evidenced.

## Stack (provisional baseline, D-010 — validate in scaffold/CI)
- **Backend:** Python 3.14.x, Django 5.2 LTS, Django REST Framework, PostgreSQL 18, Redis 8, Celery, Gunicorn
- **Frontend:** React 19, TypeScript, Vite, React Router
- **Infra:** Docker / Docker Compose, env-based config

## Repository layout
- `backend/` — Django + DRF application (`config/`, `apps/core|institutions|accounts|permissions|audit|guardians|admissions|students|imports|employees|academics|teaching|attendance|examinations|transcripts|alumni`)
- `frontend/` — React + TypeScript (Vite) auth/dashboard shell
- `infrastructure/` — deployment/infra assets
- `docs/architecture/` — living architecture/status docs updated through M4
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
- Backend: `ruff check apps config` pass; `python manage.py check` pass; `python manage.py makemigrations --check --dry-run` pass; `pytest -q` pass (**68 tests** against PostgreSQL 18), including object-level scoped querysets, canonical-role and negative API tests, cross-scope/IDOR denial, audit-chain tamper detection, report-card PDF/hash/snapshot/download, effective-dated grading policy, timetable recurrence/publish, teacher attendance, and graduation→alumni linkage.
- Audit integrity: `python manage.py verify_audit_chain` reports the chain valid.
- Frontend: `npm run lint`, `npm test` (**17 Vitest tests**), `npm run build` (`tsc -b && vite build`), and `npm run test:e2e` (**2 mocked Playwright specs**) all pass.
- Backend dependencies pinned via `backend/requirements.txt` and `backend/requirements-dev.txt` (pip freeze snapshot); `frontend/package-lock.json` committed.
- Remote CI: historical runs were green through transcript code commit `a603498` (`44769870049`, `44775171408`, `45130273958`, `45135466158`, `45136374503`, `45149166162`). Closure commit `d59f744` initially failed audit verification (`45217310279`) because CI did not migrate the service database first; CI fix `a7cfb58` added the migration and rerun `45218305149` passed backend lint/check/migration/tests/audit verification and frontend lint/unit/build/E2E.
- **Not yet validated here:** containerized backend/Celery runtime (Docker Desktop stalls at image export) and Celery/Redis task integration.

## Current status
- **Documented/approved:** Phase 0 baselines, D-010 validated, RBAC matrix approved as the MVP authorization baseline (D-026), Phase 2/M2 accepted and Phase 3 authorized (D-027). Q-001–Q-012 tracked (non-blocking for foundation).
- **Implemented (foundation):** env-driven Django/DRF config, custom `accounts.User` (UUID/email), institutions/campus models, permissions/RBAC models/helpers, audit model/middleware/service (redaction, scope derivation, denial logging), session+CSRF auth endpoints (`/api/v1/auth/csrf|login|logout|me/`), institution/campus-scoped read APIs (`/api/v1/institutions/`, `/api/v1/campuses/`) with deny-by-default RBAC, health endpoint, initial migrations, basic frontend auth shell (login, protected dashboard, `/me` session restore), CI workflow.
- **Implemented (Phase 2 M2, closed):** guarded identifier sequences, enquiries/applications/decisions/documents, guardians, students/guardian links/lifecycle history, service-enforced transitions, duplicate-identity prevention, institution/campus-scoped APIs, configurable per-verb grants, private document storage with authenticated download, controlled student-import framework (template/preview/dry-run/errors/approval/atomic apply), audited transitions/denials.
- **Implemented (Phase 3 M3, including closure):** sessions/terms, class levels/arms, subjects/offerings, class enrolments, employee records, effective-dated teacher assignments with reassignment history, institution-scoped configurable workload policy, timetable recurrence and draft/approve/publish/revise workflow with conflict checks (teacher/class/room), teacher attendance, and student offering-based attendance sessions/marking/corrections. Object-level queryset scoping and role/negative plus cross-scope/IDOR API tests cover the M3 grants.
- **Implemented (Phase 4 M4, including closure):** configurable assessment schemes/components, effective-dated grading scales and effective-dated `GradingPolicy` (placeholder/default values pending Q-003), offering-scoped result entry with weighted scoring, submit/return/approve/publish workflow, self-approval denial, correction history with re-approval, published-only report-card snapshots, PDF report cards with private storage/hash/snapshot and authenticated download, module/verb grants, and audited transitions; transcript request/review/approve/generate/issue/correct/revoke workflow with immutable published-result snapshots, private PDF storage, QR/hash-only public verification, and version supersession; graduation→alumni linkage via `apps.alumni`. Canonical RBAC role names are used with backward-compatible aliases.
- **Implemented locally (integrity):** DB-level immutable/tamper-evident audit chain with sequenced SHA-256 hashes, update/delete-preventing PostgreSQL triggers, and `verify_audit_chain` verification command.
- **Implemented locally (frontend):** M3/M4 pages with Vitest unit tests and mocked Playwright E2E specs.
- **Not complete:** formal UAT and owner sign-off, Q-003 official grading-policy confirmation (current configurable policies are placeholders/defaults), containerized backend/Celery runtime validation, Celery/Redis integration, production hardening, provider go-live selections, and Phase 5+ domain modules.

## Governance
Per `MASTER_CRM_ERP_SCHOOL_PROMPT.md` and `DECISIONS_REGISTER.md`: no hardcoded institution rules, backend-authoritative RBAC, audited sensitive actions, preserve historical/official records. A documented decision is not an implemented/tested system.
