# Security and Privacy Plan

**Status:** Living plan. M1–M2 controls are implemented; M3/M4 add RBAC grants, privileged corrections, separation-of-duties checks, hash-only public verification, private PDF storage, object-level queryset scoping, DB-level immutable/tamper-evident audit chain, and role/negative plus cross-scope/IDOR tests. M3/M4 are accepted with formal UAT/sign-off recorded and Q-003 confirmed (D-032); production controls remain open.

## 1. Security Objectives
- Protect confidentiality, integrity, and availability of student, guardian, staff, medical, academic, and financial data.
- Enforce least privilege and strong tenant/campus/data scoping.
- Maintain auditable, tamper-evident records of sensitive actions.

## 2. Threat Considerations (high level)
- **Auth/session attacks:** credential stuffing/brute force, session hijacking, token theft, CSRF.
- **Access control failures:** IDOR, broken object/function-level auth, privilege escalation, cross-tenant/cross-campus leakage.
- **Injection & client attacks:** SQL injection, XSS, template/command injection, SSRF, open redirects.
- **Data exposure:** misconfigured storage, public access to private docs, sensitive data in logs/URLs/errors, over-broad exports.
- **Integrity/fraud:** unauthorized result/grade/transcript changes, payment spoofing/duplicate posting, unauthorized refunds/reversals.
- **Availability:** abuse/DoS on auth/public endpoints, unbounded queries/exports.
- **Supply chain/config:** vulnerable dependencies, leaked secrets, insecure defaults.

## 3. Authentication & Session Security
- Strong password hashing via Django-supported hashers; password policy and secure reset (time-limited, single-use tokens).
- Recommended: HttpOnly, Secure, SameSite cookies with CSRF protection for state-changing requests; alternative token flow must use short-lived access + rotating revocable refresh, never stored long-lived in localStorage (D-011).
- Login throttling/rate limiting, account lockout/alerts as configured; optional MFA (configurable/later as planned).
- Secure logout/invalidation; session/device management where feasible.

## 4. Authorization & Data Isolation
- Deny-by-default RBAC with scoped permissions (institution/campus/class/subject/record/own) per RBAC matrix.
- Enforce checks in querysets, serializers/views, services, and background jobs; object-level checks to prevent IDOR.
- Strict institution/campus scoping on every owned record and access path; no reliance on frontend filtering.
- Segregation-of-duties and (where configured) second approval for sensitive actions (results publish/correction, transcript issue/correction, financial reversals/refunds, permission escalation).
- **M3 implemented:** deny-by-default module/verb grants for `employees`, `academics`, `teaching`, `attendance`; `my-assignments` and attendance service methods enforce teacher-scoped checks; attendance corrections require reason and privileged approval grants.
- **M4 implemented:** deny-by-default `examinations` grants; assigned-offering enforcement for teacher result entry; self-approval denial; exam-officer/principal approval and publication grants; reason-required corrections with preserved prior values.
- **M4 transcript implemented:** deny-by-default `transcripts` grants; institution/campus-scoped querysets; request self-approval denial; reason-required rejection/correction/revocation; authenticated private PDF download; public token verification that stores only hashes and returns no student personal data.
- **M3/M4 closure:** object-level queryset scoping is applied to implemented APIs; role/negative and cross-scope/IDOR tests cover M3/M4 grants. Canonical role names match the matrix with backward-compatible aliases (`Academic Head`, `Teacher`, `Principal`, `Principal/VP`). Formal UAT/sign-off and Q-003 confirmation are recorded under D-032.

## 5. Application & API Security
- Input validation (server-side authoritative), output encoding, parameterized ORM/queries (no raw SQL injection), safe file handling.
- CSRF protection for cookie-auth flows; CORS restricted to trusted origins.
- Rate limiting/throttling on sensitive and public endpoints (auth, password reset, public forms, webhooks as appropriate).
- Consistent error handling without leaking sensitive/internal details; 401/403/404 semantics to avoid unauthorized disclosure.

## 6. Data Protection & Privacy
- **Data classification:** identify public, internal, confidential, and highly sensitive (medical/welfare, credentials, financial, minors' data) categories.
- **Minimization:** collect/store only necessary fields; restrict visibility (e.g. medical info to specifically authorized roles).
- **Encryption:** TLS for data in transit; encryption at rest via supported DB/infra/storage controls; secure key/secret management.
- **PII handling:** avoid PII/sensitive data in logs, URLs, or client storage; mask/redact where needed.
- **Consent & preferences:** record consent where required (communications, optional data use); honor communication preferences.
- **Retention & lawful handling:** configurable retention periods by record type/legal requirement; support authorized access/correction requests; anonymization/deletion only where lawful and approved; **preserve official academic and financial records** per obligations.
- **Children/minors:** heightened care, restricted access, and policy-aligned handling.

## 7. File & Document Security
- Validate extension, MIME type, size; safe generated storage names; malware-scan integration point.
- Private documents stored outside public web roots in private buckets/paths; access via authenticated endpoints or short-lived signed URLs **after** authz checks.
- Transcript and report-card PDFs are private-by-default, stored via `private_document_storage`, and served only through RBAC/scope-checked download endpoints with audit events; report-card records retain hash and snapshot metadata.
- Verification tokens are high-entropy random values; only SHA-256 hashes are persisted for lookup, QR/text embeds the verification path, and public outcomes exclude student identifiers.
- Separate public CMS media from confidential ERP documents; explicit publication controls.

## 8. Audit Logging & Integrity
- Immutable/tamper-evident audit records for: logins/security events, user/role/permission changes, student/teacher-allocation/attendance/result/report-card/transcript/finance/CMS/export/import sensitive operations (per Master Spec §28).
- Capture actor, action, target, timestamp, reason (where relevant), safe change summary; restrict read access and prevent ordinary modification/deletion.
- M3 writes application-level audit events for assignments, timetable slots/publish transitions, attendance marking/closing/corrections and teacher attendance; M4 writes events for scheme/component/scale/policy configuration, result recording/submission/review/approval/publication/correction, report-card generation/download, transcript request/approval/generation/issue/correction/revocation/download, verification outcomes, and alumni linkage.
- DB-level immutability/tamper-evidence is implemented: sequenced per-institution/global hashes with predecessor linkage, unique sequence/hash constraints, `editable=False` timestamps, and PostgreSQL triggers rejecting UPDATE/DELETE on `AuditLog`. `python manage.py verify_audit_chain` verifies sequence, predecessor hash and entry hash integrity (optionally `--institution-id`); local verification is valid.
- Official records (results, transcripts, posted finance, IDs) managed via controlled workflows, versioning, and reversals—no silent destructive edits.

## 9. Dependency, Infrastructure & Operations Security
- Pin dependencies and lockfiles; automated vulnerability/dependency scanning in CI; timely patching.
- Hardened container/host configs, least-privilege service accounts, network segmentation as applicable, secrets manager/env-based config.
- Backups encrypted/stored securely; tested restores; monitoring/alerting for anomalies and security events.

## 10. Secure SDLC & Verification
- Security requirements and threat-aware reviews in design (Phase 0 onward).
- Automated tests: authn/authz positive & negative (incl. cross-tenant/campus/IDOR), workflow/state integrity, input validation, file access controls.
- Current local evidence: `pytest -q` -> 68 passed against PostgreSQL 18, `verify_audit_chain` valid, `npm run lint` pass, `npm test` -> 17 passed, `npm run build` pass, `npm run test:e2e` -> 2 mocked specs passed. Coverage includes teacher scope, object-level/IDOR denial, role/negative API tests, approval/publication API denials, transcript/report-card private PDF download, public verification outcomes, and audit-chain tamper detection. CI config includes backend audit-chain verification and frontend lint/E2E; closure remote CI run `45218305149` passed after `a7cfb58` fixed the missing migration step that caused `45217310279` to fail.
- Pre-production: security review, dependency scan, configuration review; periodic reassessment.

## 11. Open Items (Pending)
- Confirm compliance/regulatory obligations applicable to the institution/jurisdiction.
- Finalize data retention schedule and incident response contacts/runbook (with Ops plan); D-011 secure-cookie/CSRF flow is implemented.
- Provider DPAs and data residency/processing terms (integrations/storage).
- M3/M4 acceptance gates: **closed** — formal UAT/sign-off on the locally validated security controls and Q-003 official policy confirmation recorded by owner instruction (D-032); remote CI evidence is green (`45218305149`).
- Containerized backend/Celery runtime and Celery/Redis integration remain separate infrastructure validation items.
