# Implementation Roadmap

**Status:** Living roadmap (Phase 0 documented; Phase 1 foundation accepted; Phase 2/M2 accepted and closed per D-027; M3/M4 accepted with formal UAT/sign-off recorded and Q-003 confirmed per D-032). Sequenced by dependencies and Master Spec Phases 0–7.
**Last updated:** 2026-11-24

## 1. Guiding Approach
- Complete Phase 0 (this blueprint) with reviews/approvals before broad feature coding.
- Deliver MVP (Release 1) as stable, end-to-end workflows; defer R2/R3 per scope.
- One module/vertical slice at a time; backend rules authoritative; tests and docs with each increment.
- No claim of completion without implementation and test evidence.

## 2. Phases, Dependencies & Milestones

### Phase 0 — Discovery & Architecture
- **Deliverables:** 13 architecture docs + readiness report, ERD/data dictionary, RBAC/workflows/API, compatibility/integration/security/test/deployment plans, decisions register.
- **Exit criteria:** critical conflicts resolved, mandatory decisions approved or explicitly pending with owners, DB/app boundaries reviewed, MVP acceptance criteria agreed.
- **Gate:** **CONDITIONAL GO** recorded; M1 accepted (D-010/D-011/D-020 validated with follow-ups), Phase 2/M2 closed (D-027), and Phase 3/M3 plus Phase 4/M4 accepted (D-032).
- **Status:** **Documented/complete for baseline planning.** Formal owner evidence and external inputs (Q-001–Q-012) remain tracked.

### Phase 1 — Foundation (depends on Phase 0 CONDITIONAL/GO + approved pins/auth)
- **Scope:** repo/project structure, backend/frontend scaffolds, env/config, Docker dev setup, institution/campus context, authn (per D-011), RBAC framework, audit framework, base UI system, CI pipeline, initial tests, OpenAPI scaffolding.
- **Milestone M1:** authenticated user can log in (securely) to correct institution/campus context with enforced RBAC and audit of auth/security events; CI green.
- **Dependencies:** D-010 (versions/lockfiles), D-011 (auth choice), D-014 (storage approach), core ERD for identity/tenancy.
- **Status (2026-11-20):** **M1 accepted to proceed.** Implemented: Django/DRF scaffold, env-driven config, custom `accounts.User`, institutions/campus, permissions & audit app scaffolds/services, session+CSRF auth endpoints + basic frontend auth shell, initial migrations, CI workflow, backend/frontend dependency snapshots. Institution/campus-scoped read APIs enforce deny-by-default RBAC with object-level institution/campus checks and audited denials; audit service now redacts secrets, derives scope and logs write failures. RBAC role/permission matrix approved as MVP baseline (D-026). Validation: `ruff check apps config`, `manage.py check`, `makemigrations --check --dry-run`, `pytest -q` (**15 passed**) against PostgreSQL 18; frontend build passed; remote CI green (`44763428401`); Postgres 18 + Redis 8 containers healthy. **Remaining hardening (non-blocking at M1):** per-module RBAC grants/enforcement and EOL/lockfile-tooling follow-ups; containerized backend/Celery runtime and Celery/Redis integration were validated locally later (D-033).

### Phase 2 — Student & Admissions (depends on M1)
- **Scope:** enquiries, applications, admissions workflow, student profiles, guardian relationships, lifecycle transitions, document management, controlled imports groundwork.
- **Milestone M2:** enquiry→application→approval→enrolment works end-to-end with unique admission number, no duplicate identity, linked guardians, audited transitions.
- **Dependencies:** identity/ID generation, file storage (private), RBAC scopes.
- **Status (2026-11-20):** **M2 accepted and closed (D-027).** Implemented identifier sequences, enquiries/applications/decisions/documents, guardians, students/guardian links/lifecycle events, service-enforced workflows, duplicate-identity prevention, institution/campus-scoped APIs with module role grants, private document storage/import-validation groundwork, and audited transitions/denials. Validation: `ruff check apps config`, `manage.py check`, `makemigrations --check --dry-run`, `pytest -q` (**25 passed**) against PostgreSQL 18; remote CI green (`44769870049`) for the M2 slice and (`44775171408`) for closure commit `5bea736`. Provider-dependent production integrations remain tracked; containerized backend/Celery runtime and Celery/Redis integration were validated locally later (D-033), not M2 blockers.

### Phase 3 — Academic & Teaching (depends on M2)
- **Scope:** academic sessions/terms, class levels/arms, subjects/offerings, employee/teacher records (base), subject-teacher allocations (effective-dated/history), draft/versioned timetables with add-slot conflict checks, student offering-based attendance (teacher attendance remains planned).
- **Milestone M3:** configured structure with valid teacher allocations and timetable conflict checks; attendance marking/corrections audited; teacher scoped to assigned classes/subjects.
- **Dependencies:** academics/teaching schema, conflict validation services.
- **Status (2026-11-23; acceptance recorded per D-032):** **M3 accepted.** Added academic sessions/terms, class levels/arms, subjects/offerings, class enrolments, employee records, effective-dated teacher assignments with reassignment history, institution-scoped configurable workload policies, recurring draft/approve/publish/revise timetable slots with conflict checks (teacher/class/room), `/teacher-assignments/my-assignments/`, teacher attendance, and student offering-based attendance sessions/marking/corrections with audit trail and privileged correction policy. Object-level queryset scoping, canonical role names with aliases, and role/negative plus cross-scope/IDOR API tests are implemented. Validation: closure `ruff check apps config`, `manage.py check`, `makemigrations --check --dry-run`, `pytest -q` (**68 passed** total) against PostgreSQL 18; historical M3 commit `d5c293a` passed remote CI `45130273958` with 29 tests, and closure CI passed at `a7cfb58` (`45218305149`). Formal UAT/sign-off is recorded by owner instruction and Q-003 is confirmed (D-032).

### Phase 4 — Examinations & Transcripts (depends on M3)
- **Scope:** assessment schemes/components, grading scales (effective-dated), result entry/validation, submission→review→approval→publish workflow, corrections/versioning, report cards (PDF), cumulative transcripts (generation/issuance/verification/versioning), graduation→alumni linkage, basic ID cards (if sequenced per MVP).
- **Milestone M4:** assigned teacher submits results; controlled approval/publish; published report cards; official verifiable cumulative transcript from approved historical results; graduation links alumni; correction histories preserved.
- **Dependencies:** teaching assignments/scopes, document/PDF generation, verification tokens/endpoints.
- **Status (2026-11-23; acceptance recorded per D-032):** **M4 accepted.** Added `examinations` app with assessment schemes/components, effective-dated grading scales and `GradingPolicy`, weighted result scoring, submit/return/approve/publish workflow with self-approval denial, correction history with re-approval, published-only report-card snapshots, PDF report cards with private storage/hash/snapshot and authenticated download, audited transitions, module/verb grants, service tests, and role/negative plus cross-scope/IDOR API tests. Added `transcripts` app with request/review/approve/generate/issue/correct/revoke workflow, immutable published-result snapshots, private PDF storage, QR/hash-only public verification, and version supersession; graduation→alumni linkage is implemented via `apps.alumni`. Added DB-level immutable/tamper-evident audit chain with hash verification, and M3/M4 frontend pages with 17 Vitest tests and 2 mocked Playwright specs. Validation: closure `ruff check apps config`, `manage.py check`, `makemigrations --check --dry-run`, `pytest -q` (**68 passed** total), `verify_audit_chain`, `npm run lint`, `npm test`, `npm run build`, and `npm run test:e2e` all pass locally on PostgreSQL 18; historical remote CI runs include `45135466158` and `45149166162`, and closure CI passed at `a7cfb58` (`45218305149`). Formal UAT/sign-off is recorded by owner instruction and Q-003 is confirmed (D-032).

### Phase 5 — Finance & Portals (depends on M2, M3 context)
- **Scope:** fee categories/schedules, invoices, payments (server-verified, idempotent), receipts/balances, refunds/reversals/adjustments, parent portal, teacher portal, notifications (in-app/email/SMS as available), basic dashboards.
- **Milestone M5:** invoice→verified payment→receipt/balance accurate (no duplicates); parent sees only linked students/approved info; teacher sees assigned scopes; notifications logged.
- **Dependencies:** D-012/D-013 providers or sandbox/mocks; finance domain services.

### Phase 6 — Public Website & CMS (depends on M1; can parallelize partially)
- **Scope:** public site pages, CMS admin (pages/menus/media/news/events/gallery), draft/review/publish/schedule, revisions, SEO/metadata/redirects, branding; strict public/private separation.
- **Milestone M6:** authorized editor publishes content visible publicly; drafts/private ERP data never exposed; CMS audited.
- **Dependencies:** storage for public media, RBAC for CMS roles.

### Phase 7 — Hardening & Production Readiness (depends on M1–M6)
- **Scope:** security review, performance/load testing vs targets, accessibility (WCAG 2.2 AA) checks, backup/restore drill, data import validation, UAT, deployment/ops/runbooks, admin/user guides, release checklist, production orchestration/sizing and prefork tuning, monitoring/alerting. Local container runtime validation is already recorded in D-033.
- **Milestone M7 (MVP Release Candidate):** MVP acceptance criteria satisfied (Master Spec §38), restore demonstrated, docs complete, known limitations recorded.
- **Gate:** production release approval.

## 3. Cross-Cutting (throughout)
- RBAC/audit enforced per feature; migrations reviewed; tests (unit/integration/permission/E2E) added continuously; OpenAPI schema is wired and M1–M4 backend endpoint documentation, including transcript verification, is concrete in `API_DESIGN.md`; later domains remain illustrative; no hardcoded institution rules.
- Minimal environment-validation scaffold allowed early but must not bypass Phase 0 gates.

## 4. Release 2 / 3 (post-MVP, separate planning)
- **R2:** full double-entry accounting/GL integration, HR/leave/payroll (configurable, reviewed), full inventory/procurement/asset mgmt, library, transport, hostel, LMS, full alumni portal, advanced analytics.
- **R3:** WhatsApp, biometric, GPS, online exams, AI-assisted analytics, multi-institution SaaS/billing (requires tenant strategy), additional integrations.
- Each requires its own detailed design, approvals, and acceptance criteria.

## 5. Key Dependencies & Risks (summary)
| Dependency/Risk | Impact | Mitigation |
|---|---|---|
| Remaining unapproved/pending inputs (Q-001–Q-002, Q-004–Q-006; Q-003 accepted per D-032) | Rework in integrations/infrastructure | Track with owners; use adapters/config |
| Auth choice & version pinning | Security/compatibility | Verify and decide before M1 |
| Provider credentials (payment/SMS/email) | E2E payment/notification validation | Adapter + sandbox/mock; integrate when available |
| Complex domain rules (grading/transcripts/finance) | Correctness/audit risk | Configurable rules, controlled services, strong tests |
| Q-003 official grading/CA/promotion/workload/report-card policy | Accepted (D-032) | Configurable effective-dated policies are the accepted institutional baseline; future changes follow policy change control |
| M3/M4 closure remote CI evidence | Evidence closed | Commit `a7cfb58` passed run `45218305149` after initial `45217310279` missing-migration failure was fixed |
| Containerized backend/Celery runtime and Celery/Redis integration | Local validation closed (D-033); production orchestration remains separate | Direct and Compose backend image builds, healthy services, health endpoint DB/cache ok, `verify_runtime`, real `core.ping` execution, persisted beat schedule; production prefork tuning, monitoring and provider integrations remain Phase 5/production concerns |
| Data migration quality | Go-live integrity | Dry-run, validation, reconciliation, audit |

## 6. MVP Acceptance Alignment
Roadmap milestones M1–M7 map to Master Spec §38 acceptance areas: admissions, academic/subject-teacher allocation, results/report cards, cumulative transcripts, finance, portals/CMS, inventory/asset/procurement (MVP scope), security/ops (incl. cross-scope denial, audits, backup restore proven).

*Dates/effort not estimated here (team/capacity unknown); to be planned once team and approvals are confirmed.*
