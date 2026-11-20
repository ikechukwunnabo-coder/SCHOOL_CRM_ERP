# Gaps & Improvements Before Implementation

`CRM_ERP_SCHOOL_PROMPT.md` is comprehensive, but the following should be clarified/tightened before implementation to reduce ambiguity and rework.

## 1. Scope & Product Decisions
- **Resolve open choices (left in DOCX):** v1 institution type (Nursery/Primary/Secondary only vs tertiary/configurable), deployment model (single school multi-campus now vs future multi-school SaaS/tenant isolation), and confirm the public site is an integrated CMS (MD assumes; DOCX questioned).
- **Define MVP vs later:** 12 phases/30+ modules is large; mark must-have vs optional/deferred (e.g. WhatsApp, biometric/QR, GPS, AI analytics, WAEC/NECO, online classes, specific payment gateways) and a realistic first-release slice.
- **Locale/regulatory context:** state target country/region assumptions (grading norms, calendar, payroll/tax/statutory deductions, currency) or require them as configurable inputs.

## 2. Tech Stack & Architecture Specifics
- **Pin versions/compatibility:** exact Python, Django/DRF/Celery, Node, React, PostgreSQL versions and package manager; verify stated versions (e.g. “Django 5.2 LTS”) and compatibility.
- **Auth model clarity:** “JWT with secure session management” is ambiguous—define token type/storage, refresh/rotation/revocation, cookie vs header, and CSRF/session implications.
- **Tenancy/campus data model:** specify now vs future: tenant/school/campus identifiers, isolation strategy, and how data/permissions are scoped (critical if SaaS-capable later).
- **Module boundaries/ownership:** clarify overlaps (e.g. `academics` vs `subjects`/`teachers`/allocations; promotion/graduation/alumni ownership; CRM vs alumni module; where timetables/curriculum live) to prevent duplicate models/logic.

## 3. Domain & Business-Rule Detail
- **IDs & identity:** format/scope for student/admission/employee/transcript/alumni numbers; uniqueness rules.
- **Academic rules:** structures per level, assessment schemes/weightings per subject/class/term, grade scales & promotion rules, class/arm/subject enrollment constraints, and how historical grading scales are versioned/preserved.
- **Subject–teacher edge cases:** co-teachers/assistant roles vs who owns/enters/submits results; conflict rules; allocation history semantics.
- **Results/transcripts:** correction/versioning workflow for approved results (who can authorize, states, audit), definition of “approved/complete” for official transcripts, and handling/presentation of incomplete records.
- **Lifecycle transitions:** transfer/withdrawal/readmission, promotion, graduation→alumni activation—state machine, data retention/linkage, and effect on access/finance.
- **Finance:** currency (and multi-currency?), tax/levies, discounts/scholarships/bursaries rules, installment/refund/credit-note/adjustment workflows, payment allocation/reconciliation, and gateway reconciliation behavior.
- **HR/Payroll:** salary components and statutory deductions/benefits (locale-dependent)—define configurability or explicit assumptions.

## 4. RBAC, Security & Compliance
- **Concrete permission model:** how module/action/campus/department/record-level permissions are represented and managed (role-permission matrix/defaults), comprehensive data-segregation rules, and scope/audit of “administrative overrides.”
- **Sensitive-action authority:** who can approve/publish results, issue/correct/verify transcripts, post/reverse/refund financials, change roles/permissions.
- **Privacy/compliance:** data classification/retention/deletion (and “soft delete” vs legal erasure), consent handling, medical-data restrictions, and any target compliance standards.
- **Security ops:** file upload constraints (types/size/scanning), secrets management, rate-limiting/throttling policy, encryption at rest/in transit specifics.

## 5. Integrations & External Dependencies
- **Name targets or define interfaces:** payment gateways, SMS/email/WhatsApp providers, biometric devices, GPS—API/credential handling, webhooks, idempotency, failure/retry, and reconciliation (many listed as configurable/optional without contracts).
- **Storage:** S3-compatible provider/buckets, dev vs prod strategy, media access control for sensitive documents.

## 6. Non-Functional Requirements & Operations
- **Quantify NFRs:** performance/concurrency, report/transcript generation expectations, availability, and backup/restore targets (RPO/RTO).
- **Quality/UX baselines:** accessibility standard (e.g. WCAG level), supported browsers/devices, i18n/timezone/date-number formats.
- **Delivery/ops:** environments (dev/stage/prod), CI/CD, logging/monitoring/alerting, migration/seed strategy (including import of existing data), and test strategy/coverage expectations.

## 7. Document Consistency & Usability
- **Add glossary & assumptions:** define terms (session/term/semester, arm/section, broadsheet, etc.) and record explicit assumptions/decisions.
- **Reconcile inconsistencies:** duplicated/overlapping items (e.g. alumni in CRM and as dedicated module), align prescribed frontend/app structures, and ensure acceptance criteria reflect the agreed MVP/scope.

**Recommendation:** add a “Decisions/Assumptions & MVP Scope” section to the master spec and resolve the above before Phase 1.
