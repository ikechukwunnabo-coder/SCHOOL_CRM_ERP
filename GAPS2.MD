# Feedback: MASTER_CRM_ERP_SCHOOL_PROMPT.md (Gaps/Observations)

**File:** `MASTER_CRM_ERP_SCHOOL_PROMPT.md` (1,828 lines, read in full)  
**Status:** Positioned as the **authoritative master prompt, technical specification & implementation brief** (superseding/refining `CRM_ERP_SCHOOL_PROMPT.md`).

## Summary
A substantially more comprehensive and implementation-ready spec than the earlier prompt. It defines clear baseline decisions, staged scope, architecture, domain rules, security/NFRs, QA/ops, and delivery/acceptance criteria.

## What it covers well (key points)

### Baseline decisions & scope (§2–3)
- Nursery/Primary/Secondary, Nigeria (`NGN`, `en-NG`, `Africa/Lagos`, `DD/MM/YYYY`), 1 institution w/ multi-campus (data-model ready for future multi-institution, not public SaaS now), integrated CMS, modular monolith (Python/Django 5.2 LTS+DRF, React+TS, PostgreSQL). Configurable rather than hardcoded.
- Requires a **Decisions & Open Questions Register** pre-implementation.
- Staged scope:
  - **Release 1 MVP (18 items):** auth/RBAC, config, CRM/admissions/enrolment, guardians, basic staff, academics (sessions/terms/classes/arms/subjects), subject–teacher allocation, timetable, attendance, CA/exams, result workflow, report cards & cumulative transcripts, basic fees/invoices/payments, parent & teacher portals, integrated CMS, dashboards/reports/notifications/audit, graduation→alumni linkage, basic asset register.
  - **Release 2:** full double-entry accounting/GL, HR/leave/payroll, full inventory/procurement/asset mgmt, library, transport, hostel, LMS, full alumni portal, advanced analytics.
  - **Release 3 (optional):** WhatsApp, biometric, GPS, online exams, AI analytics, multi-institution SaaS, integrations.

### Stack & engineering (§4)
- Verify/pin exact compatible versions/lockfiles (Python 3.14+, Django 5.2 LTS, supported PostgreSQL, Redis, Celery, Gunicorn/Nginx; React TS strict, Vite, Tailwind, shadcn/ui, TanStack Query, RHF+Zod, Recharts).
- Docker dev/stage/prod, CI, migrations, logging/monitoring, backups/restore, docs.
- Prescribed root layout (`backend/ frontend/ infrastructure/ docs/ scripts/ tests/ …`, `school_erp_venv/` uncommitted).

### Architecture & isolation (§5–6)
- Modular monolith with clear app ownership (`core, institutions, accounts, permissions, students, admissions, guardians, employees, academics, teaching, attendance, examinations, transcripts, finance, inventory, procurement, asset_management, communications, portals, cms, alumni, reporting, audit, integrations`), no duplicate entities/circular deps.
- Institution/campus context on records, enforced in API/services/jobs (no frontend-only filtering), cross-institution/campus access tests.

### Auth & RBAC (§7)
- Prefer secure HttpOnly cookie auth + CSRF (or short-lived access + rotating/revocable refresh), throttling, timed single-use reset, optional MFA; never long-lived tokens in localStorage.
- Granular deny-by-default RBAC, configurable multi-roles, scoped (institution/campus/assigned class|subject|record/own), actions incl. submit/review/approve/publish/export/print/reverse/refund/issue/revoke.
- Auditable sensitive actions; possible second approver for critical ops.

### Core domain rules (§8–24)
- **CRM/admissions & lifecycle:** configurable workflows, convert without duplicate identity, configurable IDs; longitudinal records with audited transitions & preserved history.
- **Guardians:** many-to-many, controlled access.
- **Academics:** configurable/historical structures.
- **Subject–teacher allocation (core):** dedicated model (session/term/role/effective dates/status/workload/history, lead/assistant/substitute, reassignment, conflict/workload checks) with scoped teacher authority and audit.
- **Timetables & attendance:** conflict validation/versioning; corrections with audit.
- **Identity cards:** student/staff auto-generated from biodata, templates/branding, PDF/CR80 & A4, QR verification via secure non-guessable token (limited status only), issuance lifecycle, revoke/replace history, RBAC/audit.
- **Exams/results:** configurable (no hardcoded grading), scoped entry/validation, controlled workflow (Draft→Submitted→Returned→Resubmitted→Approved→Published), no self-approval by default, no silent edits—formal versioned corrections, recalculation via controlled services.
- **Report cards:** from approved/published data only.
- **Cumulative transcripts (mandatory):** approved historical results, preserve grading scheme at time earned, provisional/incomplete handling, unique ref, secure verification, issuance/reissue/correction with version history.
- **Graduation/alumni:** preserves record and creates/activates linked alumni (no duplicate).
- **Finance MVP:** fees/invoices/payments/receipts/balances; server-side gateway verification, idempotency, no mark-paid-on-redirect, no delete posted txns—reversal/adjustment with audit, currency on txns; designed for R2 double-entry GL.
- **HR/payroll:** configurable/effective-dated (no hardcoded statutory rules).
- **Portals:** parent/teacher/student; alumni R2 (separate/privacy).
- **CMS:** integrated but strictly separated from private ERP data (draft/review/publish, revisions, SEO/redirects).
- **Communications:** consent/preferences; avoid sensitive data in insecure channels.
- **Inventory vs asset mgmt vs procurement:** distinguished and integrated (stock ledger/movements/controls; serialized assets with custody/maintenance/depreciation/disposal history; requisition→PO→GRN→invoice matching, segregation-of-duties, traceability to finance/GL) plus library/transport/hostel extensions.

### Data, security, NFRs, QA, ops (§25–34)
- UUIDs + configurable immutable human-readable IDs (incl. asset/procurement refs); validated imports/migration.
- Privacy/least-privilege, encryption, protections (CSRF/XSS/SQLi/SSRF/IDOR), secure uploads/private storage/signed URLs, audit events for sensitive ops, retention.
- Quantified initial NFR targets (e.g. 95%<2s, 100 concurrent, reports <10s/bulk async, 99.5%, RPO 24h/RTO 8h, daily backup + quarterly restore tests, WCAG 2.2 AA) to be validated.
- Mandatory testing (model/service/API/permission/workflow/financial/result-transcript/integration + frontend + 12 critical e2e journeys, negative auth on sensitive flows). DevOps/monitoring/backup-restore and UI/UX standards.

### Delivery discipline (§35–39)
- Glossary; **Phase 0** discovery/architecture before broad coding (decisions register, ADRs, ERD/data dictionary, RBAC matrix, workflows, API conventions, etc.) → Phases 1–7 hardening.
- Strict AI-agent operating/reporting rules.
- Concrete **MVP acceptance criteria** (admissions, academic/subject-teacher allocation, results/report cards, transcripts, finance, portals/CMS, inventory/asset/procurement, security/ops incl. cross-scope denial, audits, backup restore proven).
- Final handover must distinguish implemented-tested vs UAT-needed vs partial vs planned.

## Remaining gaps / items to confirm (not fully resolved)
Addresses most items raised in `gaps.md`, but the following still require project-specific confirmation or detail (to be captured in the mandated Decisions & Open Questions Register and/or configurable rules):

1. **Exact pinned versions & compatibility:** precise Python/Node/Django/DRF/Celery/React/PostgreSQL versions and package manager/lockfiles (spec states intent to pin/verify, but not the final matrix).
2. **Provider/credential selections:** concrete payment gateway(s), SMS/email/WhatsApp providers, storage provider/buckets, and any biometric/GPS vendors/contracts (interfaces defined, targets not named).
3. **Statutory/local rules:** Nigerian grading conventions in practice, school calendar specifics, and payroll/tax/statutory deductions/benefits (spec requires configurability/effective-dating and review by qualified personnel, but no concrete rule set).
4. **NFR validation & infra sizing:** targets (load, availability, RPO/RTO) must be validated against actual infrastructure, data volumes, and load-test results.
5. **Data migration specifics:** mapping/source references for existing students/staff/results/balances if importing legacy data.
6. **Auth final choice:** cookie-based+CSRF vs token approach to be explicitly chosen/documented per deployment (both outlined, one must be selected).
7. **Module/app naming & boundaries in practice:** suggested app list may be refined during architecture design; overlaps (e.g. finance vs accounting extension, academics/teaching ownership details) to be finalized in Phase 0.

**Overall:** Strong, authoritative baseline; proceed by executing Phase 0 to resolve/record the above before broad implementation.
