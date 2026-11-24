# Test Strategy

**Status:** Living strategy. Testing is mandatory; the M3/M4 closure has local and remote CI evidence of 68 backend tests, 17 Vitest tests, and 2 mocked Playwright specs (`45218305149`). M3/M4 are accepted with formal UAT/sign-off recorded and Q-003 confirmed (D-032).

## 1. Objectives & Quality Gates
- Verify correctness of business rules, workflows, calculations, and data integrity.
- Verify security: authorization/scoping (positive and **negative**) for every sensitive workflow.
- Prevent regressions via automated CI checks.
- **Coverage guidance:** target ≥80% coverage of critical business logic, prioritizing meaningful tests over raw percentage. Critical paths and permission boundaries require explicit tests regardless of overall coverage.

## 2. Test Levels

### 2.1 Backend (pytest/Django test framework as chosen)
- **Unit tests:** models, validators, utilities, calculators (grades, totals/averages/GPA where defined, fee balances/allocations), ID generation rules.
- **Service/workflow tests:** state transitions (admissions, lifecycle, result workflow, transcript issue/correction, finance adjustments, procurement/inventory/asset flows), effective-dated logic, idempotency.
- **API tests:** endpoint contracts, serialization, pagination/filtering, validation errors, status codes, idempotency keys/webhook handling (mocked providers).
- **Permission & scope tests:** role/scope matrix enforcement, object-level/IDOR cases, cross-institution and cross-campus denial, unauthenticated access.
- **Data integrity tests:** DB constraints (unique FKs/checks), transactional atomicity, concurrency-sensitive operations (e.g. stock issuance, payment posting).
- **Integration tests:** module interactions (admissions→student→enrolment, academics→teaching→attendance, teaching→results→report/transcript, PO→GRN→stock/asset, payment verify→receipt/balance).
- **Current backend evidence (M3/M4 closure):** `ruff check apps config` pass; `python manage.py check` pass; `python manage.py makemigrations --check --dry-run` pass; `pytest -q` -> **68 passed** against PostgreSQL 18; `python manage.py verify_audit_chain` -> valid. Coverage includes object-level scoped querysets, canonical-role and negative API tests, cross-scope/IDOR denial, configurable workload policy, timetable recurrence/publish, teacher attendance, audit-chain immutability/hash verification, PDF report cards with private storage/hash/snapshot/download, effective-dated grading policy, and graduation→alumni linkage. Historical slices were 29 M3 tests, 5 M4 examinations tests and 5 transcript tests with earlier green CI runs; closure remote CI passed at `a7cfb58` (`45218305149`) after fixing the initial missing-migration failure in run `45217310279`.

### 2.2 Frontend (Vitest/React Testing Library as chosen)
- Component/unit tests for critical UI logic and rendering states.
- Form validation and submission behavior (RHF/Zod schemas aligned with API).
- Routing/protected-route and role-based UI visibility (non-authoritative) tests.
- API client/error/loading/empty-state handling.
- Accessibility checks (automated tooling e.g. axe where integrated) for key screens/components.
- **Local evidence:** `npm run lint` pass, `npm test` -> **17 Vitest tests passed** covering M3/M4 pages, permissions and API resources, and `npm run build` pass.

### 2.3 End-to-End (Playwright or equivalent)
Critical journeys (per Master Spec): 
1. Applicant enquiry → application → review/approval → enrolment (no duplicate identity, unique admission no.).
2. Student assignment to campus/class/arm.
3. Subject creation and teacher allocation (incl. conflict detection).
4. Teacher attendance marking.
5. Teacher result entry/submission (assigned scope only).
6. Result review/approval/publication; correction preserves history.
7. Parent views approved report card (linked student only).
8. Cumulative transcript generation, issuance, and verification.
9. Fee invoice creation and payment reconciliation (idempotent callbacks).
10. Student graduation and alumni linkage.
11. CMS content draft/review/publish (no private data exposure).
12. Unauthorized access attempts denied (other student/campus/institution, unassigned results).

Additional E2E as implemented: ID card generate/verify/revoke, inventory receive/issue/adjust (no unapproved negative), procurement receive routing to stock vs asset.

**Local evidence:** 2 mocked Playwright specs (`m3-workflow.spec.ts`, `m4-workflow.spec.ts`) pass via `npm run test:e2e`; they are mocked UI/workflow coverage; formal UAT/sign-off is recorded separately by owner instruction (D-032).

### 2.4 Non-Functional & Specialized
- **Performance/load (planned):** validate initial targets (response times, ~100 concurrent users, report times) against agreed infra/data; async behavior for bulk jobs.
- **Security checks:** dependency/vulnerability scans, basic SAST/config checks in CI; focused tests for CSRF/auth/session handling per chosen auth (D-011).
- **Accessibility:** target WCAG 2.2 AA; automated checks + manual review for key flows.
- **Backup/restore (ops validation):** periodic restore drill in test environment (documented evidence) — not a code test but a release gate.

## 3. Test Data & Environments
- Deterministic fixtures/factories; realistic seed/demo data **only in non-production** environments.
- Isolated test databases; reset/transactional tests; no tests against production data.
- Mock external providers (payments/email/SMS/storage webhooks) for reliability; sandbox/integration tests when credentials available (separately gated).

## 4. CI/CD Integration
- On PR/commit: lint/format, type checks (backend/frontend), unit/integration tests, build verification.
- E2E: CI runs frontend lint and Playwright E2E in addition to backend checks, including `verify_audit_chain`; closure remote CI run `45218305149` passed.
- Fail pipeline on test failures, critical lint/type errors, or coverage drop below agreed threshold for critical modules (once established).
- Publish test reports and artifacts (e.g. coverage, Playwright traces/screenshots on failure).

## 5. Traceability & Reporting
- Map tests to MVP acceptance criteria and critical workflows.
- Per phase/report: list tests executed, results (pass/fail), known gaps/defects, and untested areas (honest status).
- Defects tracked with severity, repro, and linkage to requirement/workflow.

## 6. Responsibilities & Readiness
- Developers add/update tests with every significant feature; reviewers enforce.
- QA/acceptance: UAT scenarios aligned to acceptance criteria before release sign-off.
- **No "complete" claim** without passing relevant automated tests and documented evidence.

*Tooling is implemented in the local setup (pytest, Vitest, React Testing Library, Playwright, ESLint) and recorded in CI config; coverage thresholds and staging-like E2E environments remain to be finalized.*
