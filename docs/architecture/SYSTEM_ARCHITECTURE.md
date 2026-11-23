# System Architecture

**Project:** School CRM & ERP Platform  
**Status:** Living architecture. M1/M2 are accepted; M3 modules and the M4 examinations/transcript backend are implemented locally with the listed hardening gaps closed but not accepted pending UAT/sign-off and Q-003; remaining Phase 4+ modules are proposed.
**Baseline:** Modular monolith, API-first, one institution with multi-campus (future multi-institution ready), integrated CMS.

## 1. Architectural Style & Principles
- **Modular monolith:** single deployable backend with clear domain modules/apps, communicating via documented service interfaces/domain events/APIs internally; avoid premature microservices.
- **API-first:** React (TypeScript) frontend consumes backend APIs; no frontend-only business logic for authorization or critical rules.
- **Configurable over hardcoded:** academic, finance, identity, calendar, grading, branding rules configurable/effective-dated where specified.
- **Security & integrity:** deny-by-default RBAC, server-side scope enforcement (institution/campus/record), auditable sensitive actions, immutable/history-preserving records for academic/financial/official documents.
- **Separation of concerns:** public CMS content strictly separated from private ERP data.

## 2. High-Level Component Diagram (logical)

```
[Public Website (CMS pages, public admissions info)]
        |  HTTPS (public, published content only)
        v
[React + TypeScript SPA/PWA Shell]
  - Public site  - Parent/Teacher/Student/Alumni portals  - Admin console
        |  HTTPS (API, cookie/CSRF or approved auth)
        v
[Nginx / Reverse Proxy]  --> static assets, TLS termination, routing
        |
        v
[Django + DRF Application (Gunicorn)]
  - Auth/RBAC/Permissions  - Domain modules (apps)  - Services/Workflows
  - Background job producers  - Audit logging  - File/document handling
        |           |              |
        v           v              v
 [PostgreSQL]   [Redis]     [Object Storage]
 (primary DB)  (cache,      (private docs + public CMS
               broker)       media, signed URLs)
                   |
                   v
             [Celery Workers/Beat]
             (async jobs, reports, notifications, schedules)

[External Integrations via adapters]
 - Payment gateway (webhooks, server-side verify)
 - Email / SMS (WhatsApp R3)
 - (Future) Biometric, GPS, identity services
```

## 3. Backend Application Boundaries (implemented through the M4 backend slice; later modules proposed)

| App/Module | Ownership (single source of truth) | Key responsibilities |
|---|---|---|
| `core` | Shared primitives (M1) | base models, utilities, settings helpers, common validators, ID generation services |
| `institutions` | Institution & campus (M1) | schools/institutions, campuses, tenant context, institution settings/branding config |
| `accounts` | User accounts/auth (M1) | user model/profile linkage, session+CSRF auth endpoints, `/me` |
| `permissions` | RBAC (M1, M2 closure, M3/M4 grants) | roles, permissions, scopes, policy evaluation helpers |
| `students` | Student identity & lifecycle (M2) | student record, admission number, lifecycle/state transitions, stable identity |
| `admissions` | Recruitment/admission (M2) | enquiries, applications, decisions, conversion to student (no duplicate identity) |
| `guardians` | Parent/guardian (M2) | guardian profiles, student-guardian relationships, contact/consent flags |
| `employees` | Staff identity/HR base (M3) | staff records, employee numbers, departments/job titles, employment status (payroll R2) |
| `academics` | Academic structure (M3) | sessions/years, terms, class levels/arms, subjects/offerings, class enrolments |
| `teaching` | Teaching assignments (M3) | effective-dated subject-teacher allocations, roles, timetables/slots with conflict checks |
| `attendance` | Attendance (M3 implemented) | offering-based student attendance sessions/marks, privileged corrections, teacher attendance; summaries/export refinements pending |
| `examinations` | Assessment & results (M4 implemented) | assessment schemes/components, effective-dated grading scales and policies, weighted marks entry/calculation, submission/review/approval/publish workflow, correction history, published-only report-card snapshots, private PDF report cards with authenticated download |
| `transcripts` | Official transcripts (M4 backend slice) | transcript requests/approval, published-result snapshots, provisional/official generation, private PDF storage, issuance, corrections/versioning, revocation, hash-token public verification |
| `finance` | Fees & payments (MVP) | fee categories/schedules, invoices, payments/allocations, receipts, balances, refunds/reversals; integration point for R2 GL |
| `inventory` | Stores/stock | item catalogue, stores/locations, stock movements/ledger, counts/reconciliation, alerts |
| `procurement` | Purchasing | suppliers, requisitions, approvals, POs, GRNs, invoice matching, procurement controls |
| `asset_management` | Durable assets | asset register, tagging, custody/assignment, movement, maintenance, verification, disposal, (depreciation config R2/integration) |
| `communications` | Messaging/notifications | in-app/email/SMS templates, targeting, delivery status/retries, preferences/consent |
| `portals` | Role portal aggregation | portal-specific views/endpoints composing domain data (thin; domain logic remains in owning apps) |
| `cms` | Public website/CMS | pages, menus, media, news/events/gallery, drafts/review/publish/schedule, revisions, SEO/redirects (public-only data) |
| `alumni` | Alumni | graduation-linked `AlumniRecord` records (full engagement/portal R2) |
| `reporting` | Reports/dashboards/exports | role-scoped dashboards, report generation, async exports, access logging |
| `audit` | Audit trail | immutable/tamper-evident records of sensitive actions with sequence/hash chain, DB triggers rejecting updates/deletes, and a verification command |
| `integrations` | External adapters | payment/email/SMS/(future WhatsApp/biometric/GPS) adapters, webhooks, idempotency/reconciliation hooks |

**Rules:** no duplicate business entities across apps; explicit dependency direction; no circular imports; cross-module operations via services/interfaces or domain events; all DB mutations for critical workflows wrapped in transactions.

## 4. Frontend Architecture (proposed)
- **React + TypeScript (strict)**, Vite build, Tailwind CSS + shadcn/ui (or consistent accessible components).
- **State:** TanStack Query for server state; local/UI state minimized; React Hook Form + Zod for forms/validation (client-side supplemental).
- **Structure (feature-oriented):** `app/` (bootstrap/routing/providers), `features/` (domain modules: admissions, students, academics, teaching, attendance, examinations, transcripts, finance, inventory, assets, procurement, portals, cms, reports, settings), `components/` (ui/layout/forms/tables/charts), `services/` (API client), `hooks/`, `contexts/`, `routes/` (protected/role-guarded), `types/`, `utils/`.
- **Concerns:** centralized API client with auth/CSRF handling, error normalization, pagination/filter helpers; role- and scope-aware navigation/rendering (authoritative enforcement remains backend); accessible, responsive layouts.

## 5. Data & Storage
- **PostgreSQL** primary relational DB: FKs, unique/check constraints, indexes, transactions, effective-dated/historical records, timestamps and actor refs where appropriate.
- **Redis:** caching (authz-safe, freshness-aware) and Celery broker/result backend as configured.
- **Object storage:** S3-compatible for private documents (confidential) and public CMS media (separated buckets/prefixes/policies); signed/expiring URLs or authenticated download endpoints for private files.
- **Identifiers:** stable internal PKs (UUIDs where appropriate) + configurable human-readable immutable official IDs per Master Spec §26.

## 6. Integration & Async Processing
- **Adapters:** provider-agnostic interfaces for payments, email, SMS, storage; credentials via env/secrets manager; webhook signature validation, idempotency, retries with backoff, failure inspection/replay, payment reconciliation.
- **Celery:** bulk reports/exports, notifications, scheduled tasks (reminders, expiry checks), async heavy processing; idempotent tasks where possible.

## 7. Security Architecture (high-level)
- HttpOnly/Secure/SameSite cookies (recommended) with CSRF for state changes; throttling/rate limits; strong password hashing; TLS in transit; encryption at rest via infra/storage controls.
- Authorization enforced in querysets/services/views and background jobs; object/record-level checks to prevent IDOR.
- Audit logging for sensitive operations; private-by-default documents; strict validation/sanitization of inputs and uploads.

## 8. Deployment Topology (target)
- **Environments:** dev, staging, production with separate configs/secrets.
- **Containers:** Docker Compose for local dev; production via orchestrated containers/VMs as approved (Nginx reverse proxy → Gunicorn/Django, Celery workers/beat, PostgreSQL, Redis, object storage).
- **Observability:** structured logs with correlation IDs, error monitoring/alerting, health checks.

## 9. Current implementation flows (M1–M4 backend)
- Auth/session requests → DRF views → `HasModuleVerbPermission`/institution-campus scoping → audited outcomes.
- M2 admissions/student workflows → guarded services → student conversion/import framework → private document APIs.
- M3 workflows → academics structure → effective-dated teaching assignments and configurable workload policies → timetable conflict/recurrence/publish service → offering-based student attendance and teacher attendance/corrections.
- M4 workflows → assessment scheme/grading configuration and effective-dated grading policies → assigned-teacher result entry and weighted calculation → submit/return/approve/publish transitions with separation of duties → correction/re-approval history → published-only report-card snapshots and private PDF download.
- M4 transcript workflows → transcript request/review/approval → published-result/completeness snapshot → private PDF with hash-token QR → issue/download → correction/revocation with supersession → public verification outcome logging.
- M3/M4 hardening closure: object-level queryset scoping, canonical role names with aliases, configurable workload and grading policies, timetable recurrence/publish workflow, teacher attendance, DB-level immutable/tamper-evident audit chain, PDF report cards, graduation→alumni linkage, and frontend M3/M4 pages with unit/E2E coverage. Formal acceptance still requires UAT/sign-off and Q-003; parent/student portals remain Phase 5.

## 10. Key Cross-Cutting Decisions (pending)
- Provider selections, storage provider config, and infra sizing (D-012–D-015, D-019).
- M3 acceptance gates: technical hardening implemented locally; formal UAT/sign-off remains.
- M4 acceptance gates: technical hardening implemented locally; Q-003 official grading-policy confirmation and formal UAT/sign-off remain.
- Database-level audit immutability and containerized backend/Celery runtime validation.

*This document is living architecture; implemented components are marked above and refined with each phase.*
