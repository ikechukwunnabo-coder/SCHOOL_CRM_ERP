# DECISIONS REGISTER
## School CRM & ERP Platform

**Phase:** Living implementation governance (Phase 0 baseline through Phase 3 hardening)
**Document status:** Approved for implementation (conditional) — M1 accepted, Phase 2/M2 closed, Phase 3/M3 slice implemented but not accepted
**Authoritative specification:** `MASTER_CRM_ERP_SCHOOL_PROMPT.md`  
**Revision date:** 20 November 2026  
**Primary backend runtime:** Python 3.14.x (D-010 validated in Phase 1 scaffold/CI on 2026-11-20)  
**Architecture:** Modular monolith, API-first

> **Governance statement:** This register records decisions and approaches cleared for implementation. Approval of an architectural approach does **not** mean implementation, compatibility verification, or production acceptance is complete. No feature is considered implemented or tested merely because it appears in this document. D-010 was validated in Phase 1/CI with non-blocking follow-ups; external inputs (Q-001–Q-012) remain tracked and must be resolved before affected milestones, UAT, and production go-live.

---

# 1. Confirmed Baseline Decisions

The following decisions establish the initial project direction and are approved for implementation.

| ID | Decision | Value / Baseline | Rationale / Implication | Owner | Approval |
|---|---|---|---|---|---|
| D-001 | Institution type | Nursery, Primary and Secondary | Covers the initial target institution; additional levels must remain configurable. | Product / School Management | Approved |
| D-002 | Country and locale | Nigeria, `en-NG`, `NGN`, `Africa/Lagos`, `DD/MM/YYYY` | Provides appropriate Nigerian defaults. Locale, currency, timezone and date formats must remain configurable. | Product | Approved |
| D-003 | Initial deployment model | One institution with multiple campuses | Each campus must have appropriate data ownership, access controls and reporting context. | Product / Architecture | Approved |
| D-004 | Future tenancy | Data-model ready for multiple institutions; no public SaaS in Release 1 | Avoids premature SaaS complexity while enforcing institution-level data isolation from the beginning. | Architecture | Approved |
| D-005 | Public website | Integrated public website managed through the ERP CMS | Provides centralized branding and content management while separating public content from confidential ERP information. | Product | Approved |
| D-006 | Architecture style | Modular monolith, API-first | Supports clear application boundaries without premature microservices. | Architecture | Approved |
| D-007 | Core technology stack | Python 3.14, Django 5.2 LTS, Django REST Framework, React, TypeScript and PostgreSQL | Establishes the required technology foundation. Exact compatible versions and lockfiles are governed by D-010. | Architecture | Approved |
| D-008 | Release 1 MVP scope | The 18 MVP scope items defined in `MASTER_CRM_ERP_SCHOOL_PROMPT.md` §3 | Prioritizes essential school operations before advanced extensions. | Product / Architecture | Approved |
| D-009 | Alumni and transcripts | Alumni linkage in Release 1; full alumni portal in Release 2. Cumulative transcripts must use approved historical academic records. | Preserves student lifecycle history and transcript integrity. | Product / Academic Management | Approved |

---

# 2. Technology and Architecture Decisions

## D-010 — Technology versions, compatibility and package management

**Decision:** Python 3.14.x is the approved provisional backend runtime target.

**Approval:** Approved. Exact patch versions are committed in `backend/requirements.txt`/`backend/requirements-dev.txt` and `frontend/package-lock.json`; verification evidence is recorded in `TECHNOLOGY_COMPATIBILITY_MATRIX.md` (CI runs `44761962350`, `44769870049`, `44775171408`, `45130273958`, `45135466158`, `45149166162`; PostgreSQL 18 runtime, 39 backend tests locally and in CI through transcript slice)
. Deviation: pip freeze/npm lock used instead of `uv.lock`/`pnpm-lock.yaml` because those tools are unavailable; follow-up tracked in the compatibility matrix.

### 2.1 Backend technology baseline

| Component | Recommended version | Purpose |
|---|---|---|
| Python | 3.14.x | Backend runtime |
| Django | 5.2.x LTS, latest security patch | Backend application framework |
| Django REST Framework | Latest stable compatible release | REST API development |
| PostgreSQL driver | Psycopg 3.x | PostgreSQL connectivity |
| PostgreSQL | 18.x; initially 18.7 | Primary relational database |
| Redis Server | 8.x, subject to Celery compatibility testing | Cache, broker and temporary data |
| Celery | 5.7.x or later compatible stable release | Background task processing |
| Kombu | Compatible version resolved by Celery | Message transport |
| Gunicorn | Latest stable Python 3.14-compatible release | Production WSGI server |
| Nginx | Stable supported release | Reverse proxy, TLS termination and static/media routing |
| Docker | Current stable supported release | Containerized development and deployment |
| Docker Compose | Current stable supported release | Multi-service orchestration |

**Compatibility evidence and requirements:**

- Django 5.2 supports Python 3.14 from version 5.2.8.
- Django REST Framework documents Python 3.14 and Django 5.2 compatibility.
- Psycopg 3 supports Python 3.14 and PostgreSQL versions through PostgreSQL 18.
- Celery 5.7 supports Python 3.11 and newer. The exact Celery, Kombu and Redis combination must be smoke-tested before acceptance.
- PostgreSQL 18 is a supported production release.

Official references:

- Django: https://docs.djangoproject.com/en/5.2/
- Django REST Framework: https://www.django-rest-framework.org/
- Psycopg: https://www.psycopg.org/
- Celery: https://docs.celeryq.dev/
- PostgreSQL: https://www.postgresql.org/support/versioning/

### 2.2 Recommended Django backend dependencies

The development team must evaluate and include only dependencies required by the approved architecture.

| Package | Purpose | Compatibility requirement |
|---|---|---|
| `djangorestframework` | REST API | Python 3.14 and Django 5.2 |
| `psycopg[binary]` | PostgreSQL adapter | Psycopg 3.x, Python 3.14 |
| `django-filter` | API filtering | Compatible Django release |
| `django-cors-headers` | CORS policy, if cross-origin deployment requires it | Compatible Django release |
| `drf-spectacular` | OpenAPI API documentation | Compatible DRF and Django |
| `django-storages` | Object storage integration | Compatible storage SDK |
| `boto3` | S3-compatible storage integration | Compatible Python release |
| `django-redis` | Django cache integration | Compatible Redis client |
| `redis` | Redis client | Python 3.14 and selected Redis server |
| `celery[redis]` | Background processing and Redis transport | Python 3.14-compatible Celery release |
| `django-environ` | Environment-based settings | Python 3.14 |
| `Pillow` | Image processing | Python 3.14 |
| `qrcode` | QR-code generation for ID cards and verification | Python 3.14 |
| `reportlab` | PDF generation | Python 3.14 |
| `python-dateutil` | Date and recurrence utilities where needed | Python 3.14 |
| `openpyxl` | Excel import/export | Python 3.14 |
| `python-magic` | File-type validation where supported | OS and Python compatibility |
| `argon2-cffi` | Optional password hashing backend | Python 3.14 |
| `whitenoise` | Optional static file serving | Compatible Django release |

Additional packages such as `django-guardian`, `django-import-export`, `django-mptt` or `channels` must only be introduced when a documented requirement justifies them.

Avoid unnecessary third-party dependencies and duplicate functionality already provided by Django.

### 2.3 Backend development and quality dependencies

| Package | Purpose |
|---|---|
| `pytest` | Automated tests |
| `pytest-django` | Django test integration |
| `factory-boy` | Test data factories |
| `hypothesis` | Property-based testing where valuable |
| `coverage` | Test coverage reporting |
| `ruff` | Python linting and formatting |
| `mypy` | Static type checking where adopted |
| `django-stubs` | Django typing support where compatible |
| `bandit` | Python security analysis |
| `pip-audit` | Dependency vulnerability auditing |

All development and testing dependencies must also be checked for Python 3.14 compatibility.

### 2.4 Frontend technology baseline

| Component | Recommended version | Purpose |
|---|---|---|
| Node.js | 26.x LTS | Frontend runtime and tooling |
| Package manager | pnpm | Reproducible frontend dependencies |
| React | 19.x | UI framework |
| TypeScript | 5.x or newer compatible stable release | Strict type safety |
| Vite | 7.x or newer compatible stable release | Frontend build tooling |
| Tailwind CSS | 4.x | Styling system |
| shadcn/ui | Current compatible release | Accessible UI component foundation |
| TanStack Query | 5.x | Server-state management |
| React Router | 7.x | Client-side routing |
| React Hook Form | 7.x | Form management |
| Zod | 4.x or compatible stable release | Schema validation |
| Recharts | 3.x | Dashboards and charts |
| Lucide React | Current stable release | Icons |
| Axios | Current stable release, if required | HTTP client |
| date-fns | 4.x | Date utilities |

### 2.5 Frontend development and testing dependencies

| Package | Purpose |
|---|---|
| ESLint | Code quality and linting |
| Prettier | Code formatting |
| Vitest | Unit and component tests |
| React Testing Library | Component behaviour tests |
| Playwright | Browser-based end-to-end tests |
| MSW | API mocking for frontend tests |
| TypeScript strict mode | Compile-time type safety |

### 2.6 Dependency management and version pinning

The project must use reproducible dependency management.

**Backend recommendation:**
- Use `uv` for Python environment and dependency management.
- Maintain `pyproject.toml`.
- Commit `uv.lock`.
- Use a project-specific virtual environment named `school_erp_venv` where local development requires one.
- Do not commit virtual environments or secrets.

**Frontend recommendation:**
- Use pnpm.
- Maintain `package.json`.
- Commit `pnpm-lock.yaml`.
- Use exact resolved versions through the lockfile.

**Container and deployment requirements:**
- Pin production container image versions.
- Use image digests where practical.
- Do not use floating `latest` tags for production deployments.
- Record all runtime and dependency versions in the technology matrix.
- Use automated vulnerability scanning.
- Document dependency update and rollback procedures.

**Required deliverable:** `docs/architecture/TECHNOLOGY_COMPATIBILITY_MATRIX.md`

It must record exact resolved versions, compatibility evidence, test results and approval status.

---

## D-011 — Authentication and session security

**Decision:** Adopt secure cookie-based authentication for the same-site React and Django web application.

**Recommended configuration:**
- Secure HttpOnly authentication/session cookies.
- `SameSite` cookie policy appropriate to the deployment.
- CSRF protection for state-changing requests.
- HTTPS-only production access.
- Secure session expiry and revocation.
- Password hashing using Django's supported password hashers.
- Optional MFA.
- Login throttling and account protection.
- Timed, single-use password-reset tokens.
- Session invalidation after password changes and account suspension.

Do not store long-lived access or refresh tokens in browser `localStorage`.

If future mobile applications or third-party API clients require token authentication, document a separate authentication flow rather than weakening the browser security model.

**Owner:** Security / Architecture  
**Approval:** Approved for implementation (secure cookie-based approach as specified).

## D-012 — Payment gateway

**Decision:** Use a provider-independent payment integration architecture.

Potential providers for evaluation:
- Paystack.
- Flutterwave.
- Remita.
- Other institution-approved providers.

**Required capabilities:**
- NGN payment support.
- Approved payment methods.
- Server-side transaction verification.
- Signed webhook validation.
- Idempotency.
- Reconciliation.
- Refund and reversal support.
- Transaction references.
- Payment status history.

A successful browser redirect must never independently mark an invoice as paid.

**Interim for implementation:** implement adapter interface with mock/sandbox support in dev/CI.

**Owner:** Product / Finance  
**Approval:** Approved approach for implementation. Provider/merchant credentials pending (Q-001); non-blocking for Phase 1 foundation, required before staging/production payment go-live and reconciliation UAT.

## D-013 — Email, SMS and WhatsApp providers

**Decision:** Implement provider-independent communication adapters.

**Email candidates:** Amazon SES, SendGrid, Mailgun or approved SMTP service.

**SMS:** Evaluate reputable Nigerian SMS providers based on delivery rates, sender ID approval, pricing and support.

**WhatsApp:** Defer full WhatsApp Business integration to Release 3 unless an approved business requirement changes the priority.

Required controls:
- Delivery status and failure tracking.
- Message templates.
- Consent and communication preferences.
- Retry handling.
- Rate limiting.
- Audit history.
- No unnecessary sensitive information in insecure messages.

**Interim for implementation:** configurable providers with safe dev mail/SMS mocks.

**Owner:** Product / Operations  
**Approval:** Approved approach for implementation. Provider selections and sender identities/domains pending (Q-002); non-blocking for Phase 1 foundation, required before production notification go-live.

## D-014 — File and object storage

**Decision:** Use local storage for development and private S3-compatible object storage for production.

Potential providers:
- AWS S3.
- MinIO.
- DigitalOcean Spaces.
- Another approved S3-compatible service.

Requirements:
- Separate public CMS media from private ERP documents.
- Private buckets for confidential records.
- Signed and time-limited download URLs.
- File-type and size validation.
- Malware scanning where supported.
- Encryption at rest and in transit.
- Access logging.
- Backup and retention policy.
- Controlled deletion and archival.

Student records, employee records, transcripts, financial documents and other confidential files must never be exposed through unrestricted public storage URLs.

**Owner:** DevOps / Security  
**Approval:** Approved for implementation (local dev + S3-compatible prod with separated private/public). Phase 2 closure implemented local private document storage with authenticated download; S3-compatible provider/bucket configuration remains aligned to infrastructure (Q-005/D-019).

## D-015 — Backup and disaster recovery

**Decision:** Establish automated database and file-storage backup procedures.

Initial targets:
- Daily database backups.
- PostgreSQL WAL archiving and point-in-time recovery where supported.
- Separate backup of uploaded media and documents.
- Encrypted backup storage.
- Retention policy.
- Quarterly restore tests.
- Documented disaster recovery procedures.

Initial recovery objectives:
- RPO: 24 hours or better.
- RTO: 8 hours or better.

These targets must be validated against actual infrastructure, operational requirements and budget.

**Owner:** DevOps  
**Approval:** Approved for implementation planning (targets as specified). Tooling/provider validation aligned to infrastructure (Q-005); baseline cleared for implementation planning.

## D-016 — Nigerian grading and academic calendar

**Decision:** Use configurable and effective-dated academic rules.

Requirements:
- Configurable sessions and terms.
- Different grading schemes where school policy requires them.
- Configurable continuous assessment and examination weightings.
- Configurable grade boundaries.
- Configurable promotion and progression rules.
- Preservation of the grading scheme used when historical results were earned.
- Controlled result corrections.
- School-approved report-card and transcript layouts.

WAEC and NECO-related structures must be configurable where required. Do not assume that external examination rules automatically define the school's internal grading policy.

**Interim for implementation:** fully configurable/effective-dated structures with placeholder/default seed data only until school confirmation (Q-003). No hardcoded statutory rules.

**Owner:** Academic Management / Product  
**Approval:** Approved approach for implementation. M3 added configurable session/term structures but retained a hard-coded 40-hour teacher workload cap for the initial slice; replace with school-configurable policy before M3 acceptance. Official grading/calendar policies remain pending (Q-003), required before results/transcript UAT and go-live.

## D-017 — Payroll and statutory calculations

**Decision:** Full HR and payroll functionality belongs to Release 2.

Requirements:
- Effective-dated salary structures.
- Configurable allowances and deductions.
- Statutory components and rates maintained as effective-dated rules.
- Approval history for rule changes.
- Payroll calculation audit trail.
- Payslip generation.
- Reconciliation and reporting.
- Review by qualified Nigerian payroll and accounting professionals before production use.

Do not hardcode statutory rates or assume that historical rates remain valid.

**Owner:** HR / Finance / Legal  
**Approval:** Approved approach (Release 2). No hardcoded rates; expert review required before production payroll. Non-blocking for MVP/Phase 1 foundation.

## D-018 — Legacy data migration

**Decision:** Use controlled import and reconciliation processes.

Supported formats:
- CSV.
- Excel.

Requirements:
- Standard import templates.
- Source-to-target field mapping.
- Duplicate detection.
- Data validation.
- Dry-run mode.
- Row-level error reporting.
- Import approval.
- Audit trail.
- Reconciliation of imported records.
- Rollback or controlled correction procedures.

Potential datasets:
- Students.
- Guardians.
- Employees.
- Academic history.
- Results.
- Fee balances.
- Existing asset records.
- Alumni.

**Owner:** Product / Data / School Administration  
**Approval:** Approved approach for implementation. Phase 2 closure implemented the controlled student-import framework (template, preview, dry-run, error report, approval, atomic apply); source datasets/migration scope remain pending (Q-004) and are required before any production migration.

## D-019 — Infrastructure sizing and performance

**Decision:** Treat the master specification's NFR targets as initial targets, not proven guarantees.

Initial targets:
- 95% of ordinary application requests below 2 seconds.
- Initial load-test target of approximately 100 concurrent users.
- Typical reports below 10 seconds.
- Initial availability target of 99.5%.
- Bulk processing through background jobs.
- RPO and RTO as specified in D-015.

Requirements:
- Load testing.
- Database query analysis.
- Application profiling.
- Resource monitoring.
- Capacity planning.
- Performance regression testing.

Hosting options must be evaluated against management budget, availability, security and support capacity.

**Owner:** DevOps / Product  
**Approval:** Approved targets/approach for implementation. Hosting/infra selection and budget pending (Q-005); validate via load tests before SLO claims. Non-blocking for local/dev foundation scaffold.

## D-020 — Backend application boundaries and dependencies

**Decision:** Use clearly separated Django applications with documented ownership.

Application boundaries (implemented apps marked in Phase 1/M1, Phase 2/M2, or Phase 3/M3; remaining apps proposed):

| Application | Responsibility |
|---|---|
| `core` | Shared utilities, base models and common infrastructure (M1 foundation) |
| `institutions` | Institution, campus and institutional configuration (M1 foundation) |
| `accounts` | User accounts and authentication (M1 foundation) |
| `permissions` | Roles, permissions and access policies (M1 foundation; per-verb grants in Phase 2 closure; M3 grants added) |
| `students` | Student profiles and lifecycle records (M2) |
| `admissions` | Enquiries, applications and admissions (M2) |
| `guardians` | Guardian profiles and student relationships (M2) |
| `employees` | Staff and employee records (M3 slice) |
| `academics` | Academic sessions, terms, class levels/arms and subjects/offerings (M3 slice) |
| `teaching` | Effective-dated subject-teacher allocations and timetable conflicts (M3 slice) |
| `attendance` | Student offering-based attendance; staff attendance still proposed (M3 slice) |
| `examinations` | Assessments, marks, results and approval workflows |
| `transcripts` | Cumulative transcript generation and verification |
| `identity_cards` | Student and staff identity cards |
| `finance` | Fees, invoices, payments and receipts |
| `inventory` | Stock and stores |
| `procurement` | Requisitions, quotations and purchase orders |
| `asset_management` | Fixed assets, custody and maintenance |
| `communications` | Email, SMS and notifications |
| `portals` | Parent, student and teacher portal functionality |
| `cms` | Public website and content management |
| `alumni` | Alumni records and relationships |
| `reporting` | Reports and analytics |
| `audit` | Audit events and sensitive-operation history |
| `integrations` | External provider adapters and interfaces |

Architecture rules:
1. Each business entity must have one authoritative owner.
2. Avoid duplicate models for the same business concept.
3. Avoid circular dependencies.
4. Use documented service interfaces for cross-module operations.
5. Do not allow frontend filtering to replace server-side access enforcement.
6. Financial and inventory operations must maintain transaction integrity.
7. `academics` owns academic structure; `teaching` owns subject-teacher allocation.
8. `examinations` owns result calculation and approval; `transcripts` owns official cumulative transcript issuance.
9. `identity_cards` owns card issuance, verification and revocation, not the underlying student or employee identity.
10. Finance and future general-ledger functionality must integrate through documented financial services.

**Owner:** Architecture  
**Approval:** Approved for implementation. Dependency map refined through M3: `academics` owns structure, `teaching` owns effective-dated assignments/timetable checks, `attendance` consumes offering/enrolment data; further refinement continues in Phase 4+ code review.

---

# 3. Additional Project Decisions

## D-021 — School branding and configuration

**Decision:** Centralize institution and campus branding/configuration.

Requirements:
- Institution logo and name.
- Campus details.
- School contact information.
- Brand colours.
- Public website settings.
- Document branding.
- Report-card templates.
- Transcript templates.
- Student and staff ID-card templates.
- Configurable academic and administrative settings.

Branding changes must not require source-code modification.

**Owner:** Product / School Management  
**Approval:** Approved for implementation (configurable, no source-code changes for branding).

## D-022 — Document generation and verification

**Decision:** Implement controlled document generation and verification.

Documents include:
- Student and staff ID cards.
- Student report cards.
- Cumulative transcripts.
- Admission letters.
- Certificates.
- Receipts.
- Other approved school documents.

Requirements:
- Unique document references.
- PDF generation.
- Document versioning.
- Issuance and reissuance history.
- QR verification where appropriate.
- Revocation and correction controls.
- Access permissions.
- Print-ready layouts.

QR codes must contain secure non-guessable verification references, not sensitive personal information.

**Owner:** Product / Academic / Security  
**Approval:** Approved for implementation (controlled generation/verification as specified).

## D-023 — Financial reconciliation

**Decision:** Establish financial reconciliation controls from Release 1.

Requirements:
- Invoice-to-payment matching.
- Receipt tracking.
- Outstanding balance calculation.
- Payment verification.
- Refund and reversal records.
- Duplicate transaction protection.
- Daily reconciliation reports.
- Audit history.
- Financial period reporting.

Release 2 must extend this foundation into a full double-entry accounting/general-ledger system.

**Owner:** Finance / Architecture  
**Approval:** Approved for implementation (reconciliation controls from Release 1 foundation).

## D-024 — Data retention, privacy and protection

**Decision:** Implement privacy-by-design and documented data retention.

Requirements:
- Role-based access to personal information.
- Appropriate data minimization.
- Encryption in transit and at rest.
- Secure document storage.
- Retention and archival policies.
- Controlled data export.
- Data correction procedures.
- Approved deletion and anonymization procedures where legally appropriate.
- Audit logging for sensitive access and changes.
- Data breach response procedures.

The institution must assess applicable Nigerian data protection obligations, including the Nigeria Data Protection Act and relevant regulatory guidance.

**Owner:** Management / Security / Legal  
**Approval:** Approved for implementation (privacy-by-design and retention controls as specified). Institutional legal assessment to be completed.

## D-025 — Production ownership and operational support

**Decision:** Establish explicit production responsibility before go-live.

Responsibilities must be assigned for:
- Infrastructure and hosting.
- Production administrator access.
- Database administration.
- Backup and restore.
- Monitoring and alerting.
- Security patching.
- Deployment approval.
- Incident response.
- User support.
- Disaster recovery.
- Vendor management.

No shared production administrator account should be used.

**Owner:** Management / IT / DevOps  
**Approval:** Approved requirement. Production ownership/contacts to be assigned and recorded before staging/production go-live (Q-007). Non-blocking for Phase 1 foundation.

## D-026 — RBAC role/permission baseline approval

**Decision:** Adopt the role definitions, scope-aware matrix and sensitive-action controls in `RBAC_PERMISSION_MATRIX.md` as the approved MVP authorization baseline. Deny-by-default remains mandatory; each domain phase refines per-verb grants, record-level predicates and approval thresholds as configurable data with negative authorization tests.

**Owner:** Product / Security / School Management  
**Approval:** Approved on 2026-11-20; permission granted to proceed to Phase 2 (Student & Admissions). Approval is for the documented baseline, not a claim that every matrix entry is already implemented/tested; incremental enforcement remains under Phase 2+ code review and tests.

## D-027 — Phase 2 M2 acceptance and Phase 3 authorization

**Decision:** Accept the Phase 2 Student & Admissions vertical slice as meeting milestone M2 once remote CI is green, and authorize Phase 3 Academic & Teaching implementation. Closure includes the Phase 2 residual items: private document storage groundwork, controlled-import validation groundwork, module-level per-verb RBAC enforcement and negative authorization tests.

**Evidence:** M2 slice commit `e379bef` / remote CI `44769870049` and closure commit `5bea736` / remote CI `44775171408` (frontend and backend green), local `ruff check apps config`, `manage.py check`, `makemigrations --check --dry-run`, and `pytest -q` (25 tests at closure) against PostgreSQL 18.

**Owner:** Product / School Management  
**Approval:** Approved on 2026-11-20; permission granted to close Phase 2 and proceed to Phase 3 (Academic & Teaching). Provider-dependent production integrations and containerized backend/Celery runtime validation remain tracked hardening items and do not block M3.

## D-028 — Phase 3 M3 implementation status (not accepted)

**Decision:** Record the Phase 3 Academic & Teaching vertical slice as implemented for local evidence while keeping M3 **open** until API role/negative tests, role-name alignment, configurable workload policy, timetable publish/recurrence policy, teacher attendance, and frontend/E2E workflows are complete.

**Scope implemented:** `employees`, `academics`, `teaching`, and `attendance` apps; academic sessions/terms, class levels/arms, subjects/offerings, class enrolments; effective-dated teacher assignments with reassignment history; draft/versioned timetable slots with teacher/class/room conflict checks; student offering-based attendance sessions/marking/corrections with privileged correction policy and application-level audit events; M3 module/verb grants seeded via `0004_seed_phase3_permissions.py`.

**Evidence:** Local `ruff check apps config`, `manage.py check`, `makemigrations --check --dry-run`, `pytest -q` (29 tests), and `manage.py migrate` against PostgreSQL 18. M3 commit `d5c293a` passed remote CI run `45130273958` (frontend build/tests and backend lint/checks/migration consistency/tests green).

**Owner:** Product / Engineering
**Approval:** Not an acceptance decision. The implementation is committed with passing CI; Phase 3 remains in hardening and M3 gaps remain explicitly tracked while Phase 4 proceeds.

## D-029 — Phase 4 M4 examinations backend slice (not accepted)

**Decision:** Record the initial Phase 4 Examinations backend slice as implemented for local evidence while keeping M4 **open** until PDF report cards, graduation→alumni linkage, and frontend/E2E workflows are complete.

**Scope implemented:** `examinations` app; assessment schemes/components; effective-dated grading scales; offering-scoped teacher result entry with weighted scoring; submit/return/approve/publish workflow with self-approval denial; correction records with prior-value preservation and re-approval; published-only report-card snapshots; institution/campus-scoped APIs; module/verb grants seeded via `0005_seed_phase4_permissions.py`; application-level audit events; service and API role/negative tests.

**Evidence:** Local `ruff check apps config`, `manage.py check`, `makemigrations --check --dry-run`, `pytest -q` (34 tests), and `manage.py migrate` against PostgreSQL 18. M4 commit `3f04813` passed remote CI run `45135466158` (frontend build/tests and backend lint/checks/migration consistency/tests green).

**Owner:** Product / Engineering
**Approval:** Not an acceptance decision. The backend slice is validated locally; M4 remains open and official grading policy confirmation (Q-003) is still required before transcript/report-card UAT.

## D-030 — Phase 4 M4 transcript backend slice (not accepted)

**Decision:** Record the Phase 4 transcript backend slice as implemented for local evidence while keeping M4 **open** until PDF report cards, graduation→alumni linkage, and frontend/E2E workflows are complete.

**Scope implemented:** `transcripts` app; transcript request/review/approve/generate/issue/correct/revoke workflow; published-only result snapshots that preserve historical grading-scale content; completeness detection for missing/unpublished sessions and graduation records; private PDF generation with QR verification path; hash-only verification tokens with minimal public verification responses; version supersession that invalidates prior tokens while preserving prior PDFs/snapshots; institution/campus-scoped APIs; module/verb grants seeded via `0006_seed_phase4_transcript_permissions.py`; application-level audit events; service/API role/negative tests.

**Evidence:** Local `ruff check apps config`, `manage.py check`, `makemigrations --check --dry-run`, and `pytest -q` (39 tests) against PostgreSQL 18. Transcript code commit `a603498` passed remote CI run `45149166162` (frontend build/tests and backend lint/checks/migration consistency/tests green).

**Owner:** Product / Engineering
**Approval:** Not an acceptance decision. The transcript slice is validated locally; M4 remains open, and official grading policy confirmation (Q-003) is still required before transcript/report-card UAT.

---

# 4. Open Questions Requiring Institutional Input

| ID | Question | Impact | Suggested Owner | Interim Status / Response | Blocking Phase 1 Foundation? |
|---|---|---|---|---|---|
| Q-001 | Which payment gateway and merchant account will the school use? | Online payment go-live and reconciliation | Finance / Management | **Pending.** Interim: adapter interface + mock/sandbox in dev/CI (D-012). Required before staging/production payment go-live and reconciliation UAT. | No (tracked) |
| Q-002 | Which email and SMS providers and sender identities are approved? | Notification delivery | IT / Operations | **Pending.** Interim: configurable providers with dev mail/SMS mocks (D-013). Required before production notification go-live. | No (tracked) |
| Q-003 | What are the official grading scales, CA/exam weightings and promotion rules? | Results and transcripts | Academic Management | **Pending.** Interim: configurable/effective-dated structures with placeholder/default seed only (D-016). Required before results/transcript UAT and go-live. | No (tracked) |
| Q-004 | Are there existing student, staff, financial or academic records to migrate? | Migration planning | School Administration / IT | **Pending.** Interim: implement import tooling per spec (D-018); define mappings/reconciliation when sources known. Required before any production migration. | No (tracked) |
| Q-005 | What hosting environment and infrastructure budget are available? | Deployment and sizing | Management / IT | **Pending.** Interim: local/dev scaffold and spec NFR targets (D-014/D-015/D-019). Required before staging/prod and SLO validation. | No (tracked) |
| Q-006 | Are there institution-specific regulatory, examination-board or reporting requirements? | Compliance and reporting | Management | **Pending.** Interim: configurable reporting/retention/privacy controls per spec; incorporate specifics when provided. | No (tracked) |
| Q-007 | Who is the authorized owner of the production system? | Operational accountability | Management | **Pending.** Interim: ownership to be assigned/recorded per D-025 before staging/production go-live. | No (tracked) |
| Q-008 | Who approves changes to academic grading, fees and institutional configuration? | Governance and audit | Management | **Pending.** Interim: implement approval/audit workflows per RBAC/security plans; record named approvers when provided. | No (tracked) |
| Q-009 | What student/staff ID-card fields and designs are officially required? | Identity-card implementation | Administration | **Pending.** Interim: configurable templates/fields per spec (D-021/D-022); finalize with school-approved design. | No (tracked) |
| Q-010 | What are the institution's document retention and archival requirements? | Privacy and storage | Management / Legal | **Pending.** Interim: configurable retention/archival controls per D-024; confirm legal/operational requirements. | No (tracked) |
| Q-011 | What are the approved campus structures and reporting hierarchy? | Institution and campus configuration | Management | **Pending.** Interim: configurable institution/campus structures (D-003/D-021); seed per confirmed data. | No (tracked) |
| Q-012 | What existing systems must be integrated with the platform? | Integration design | IT / Management | **Pending.** Interim: adapter-based integration architecture per specs; scope/plan integrations when identified. | No (tracked) |

Open questions must be assigned an owner and resolution deadline. An unresolved question must not be silently converted into an assumed institutional policy.

---

# 5. Technology Compatibility and Verification Requirements

Before final dependency lockfiles are accepted, the technical team must complete the following:

1. Install Python 3.14.x and create a clean backend environment.
2. Install the selected Django 5.2 LTS patch release.
3. Install the selected Django REST Framework release.
4. Verify Psycopg 3 connectivity to PostgreSQL 18.
5. Verify Redis connectivity and cache operations.
6. Verify Celery task execution, retries, scheduling and Redis transport.
7. Verify file uploads and private object storage.
8. Verify PDF generation and QR-code generation.
9. Build the React application with the selected Node.js LTS version.
10. Verify all frontend packages resolve without incompatible peer dependencies.
11. Run backend and frontend tests.
12. Build all production containers.
13. Run database migration tests.
14. Run security and dependency vulnerability scans.
15. Commit the final lockfiles and compatibility report.

**Required files:**
- `backend/pyproject.toml`
- `backend/uv.lock`
- `frontend/package.json`
- `frontend/pnpm-lock.yaml`
- `docs/architecture/TECHNOLOGY_COMPATIBILITY_MATRIX.md`

A successful package installation alone does not establish production readiness. The complete application must pass its automated test suite.

---

# 6. Phase 0 Deliverables

The following documents are mandatory:

| ID | Deliverable | Expected output | Status |
|---|---|---|---|
| P0-001 | Decisions Register | `docs/architecture/DECISIONS_REGISTER.md` | Drafted / updated (this document) |
| P0-002 | System Architecture | `docs/architecture/SYSTEM_ARCHITECTURE.md` | Drafted |
| P0-003 | Entity Relationship Diagram | `docs/architecture/ENTITY_RELATIONSHIP_DIAGRAM.md` | Drafted |
| P0-004 | Data Dictionary | `docs/architecture/DATA_DICTIONARY.md` | Drafted |
| P0-005 | RBAC Permission Matrix | `docs/architecture/RBAC_PERMISSION_MATRIX.md` | Approved (2026-11-20; D-026 MVP baseline) |
| P0-006 | Workflow Specifications | `docs/architecture/WORKFLOW_SPECIFICATIONS.md` | Drafted |
| P0-007 | API Design | `docs/architecture/API_DESIGN.md` | Drafted |
| P0-008 | Technology Compatibility Matrix | `docs/architecture/TECHNOLOGY_COMPATIBILITY_MATRIX.md` | Verified (2026-11-20; D-010) |
| P0-009 | Integration Specifications | `docs/architecture/INTEGRATION_SPECIFICATIONS.md` | Drafted |
| P0-010 | Security and Privacy Plan | `docs/architecture/SECURITY_AND_PRIVACY_PLAN.md` | Drafted |
| P0-011 | Test Strategy | `docs/architecture/TEST_STRATEGY.md` | Drafted |
| P0-012 | Deployment and Operations Plan | `docs/architecture/DEPLOYMENT_AND_OPERATIONS_PLAN.md` | Drafted |
| P0-013 | Implementation Roadmap | `docs/architecture/IMPLEMENTATION_ROADMAP.md` | Drafted |

All documents must be consistent with `MASTER_CRM_ERP_SCHOOL_PROMPT.md`.

---

# 7. Decision Status and Governance

Every decision must use one of the following statuses:

| Status | Meaning |
|---|---|
| Proposed | Recommendation documented but not accepted |
| Pending Approval | Awaiting formal owner approval |
| Approved | Formally accepted by the authorized owner |
| Approved — Verification Pending | Approach accepted; technical or operational verification remains outstanding |
| Deferred | Intentionally postponed to a later release |
| Rejected | Reviewed and not accepted |
| Superseded | Replaced by a later approved decision |

Every approved decision must record:
- Decision ID.
- Decision statement.
- Approval owner.
- Approval date.
- Supporting evidence or rationale.
- Implementation implications.
- Related requirements.
- Revision history.

Changing an approved decision requires a documented change request and impact assessment.

---

# 8. Revised Status Summary

| Category | Current status |
|---|---|
| Register documented | Yes |
| Baseline decisions identified | Yes |
| D-001–D-030 | Approved/recorded for implementation (D-010 validated in M1; D-026 approves the RBAC baseline; D-027 closes Phase 2/M2; D-028 records M3 implemented-but-not-accepted status; D-029/D-030 record M4 backend slices implemented-but-not-accepted; provider/school-policy items remain pending) |
| Python 3.14 selected as target | Yes — validated in Phase 1 scaffold/CI |
| Exact dependency lockfiles | Committed and CI-verified (pip freeze + npm lock; `uv`/`pnpm` follow-up tracked) |
| Provider selections | Pending external input (Q-001/Q-002, infra Q-005) — adapters/mocks approved for foundation |
| School-specific academic policies | Pending confirmation (Q-003) — configurable placeholders approved |
| Infrastructure selection | Pending (Q-005) — targets/approach approved |
| Architecture validation | Blueprint reviewed/documented; to be enforced and refined during implementation and code review |
| Formal owner approval evidence | Recorded in this register (subject to ongoing governance) |
| Implementation | Phase 1 foundation accepted; Phase 2 Student & Admissions vertical slice accepted; Phase 3/M3 academic/teaching slice implemented but not accepted; Phase 4/M4 examinations and transcript backend slices implemented but not accepted |
| Testing | 39 backend tests passing locally and in CI (29 at M3, 5 M4 examinations, 5 transcript); transcript CI green (`45149166162`, commit `a603498`); M4 examinations CI green (`45135466158`); M3 CI green (`45130273958`); Phase 2 closure CI green (`44775171408`); containerized backend runtime pending |

---

# 9. Phase 0 Readiness Recommendation

**Recommended status: CONDITIONAL GO — Phase 1 foundation accepted; Phase 2/M2 accepted; Phase 3/M3 slice implemented but not accepted; Phase 4/M4 examinations and transcript backend slices implemented but not accepted**

The project may proceed now with:
- Continued Phase 3 Academic & Teaching hardening per `IMPLEMENTATION_ROADMAP.md` and D-028: API role/negative tests, role-name alignment, configurable workload policy, timetable publish/recurrence, teacher attendance, and frontend/E2E workflows.
- Continued Phase 4 Examinations build-out per D-029/D-030: PDF report cards, graduation→alumni linkage, and frontend/E2E workflows.
- Completion of remaining Phase 1 hardening (containerized backend/Celery runtime, Celery/Redis integration, EOL/lockfile follow-ups) in parallel where non-blocking.
- Implementation of approved architectures/approaches (storage abstraction, adapters) without blocking on unselected providers.
- Continued refinement of ERD/data dictionary, RBAC, and API details as code is developed.

Selection of payment, SMS, email or storage providers does not block provider-independent interface development, provided the integration design is documented and approved (as recorded).

### Conditions during/after foundation start

1. Maintain the validated technology compatibility matrix and lockfiles (D-010) as dependencies change.
2. Enforce the approved authentication and authorization architecture (D-011/D-026) in each module.
3. Enforce and review database ERD/data dictionary and migrations as developed.
4. Implement RBAC per the approved matrix with negative authorization tests.
5. Finalize/refine backend application ownership and dependencies per D-020.
6. Resolve Q-001–Q-012 and external inputs before affected milestones, UAT, and production go-live.
7. Complete privacy, security, data retention, and operational readiness requirements before production.
8. Confirm MVP acceptance criteria with passing tests and documented evidence.

**Final governance principle:**

A documented decision is not automatically an implemented system. An implemented feature is not a tested feature. A tested feature is not accepted for production until the appropriate owner has reviewed and approved it.

**Authoritative project reference:** `MASTER_CRM_ERP_SCHOOL_PROMPT.md`.
