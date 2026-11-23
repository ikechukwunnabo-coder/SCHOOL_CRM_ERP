# Test Strategy

**Status:** Living strategy. Testing is mandatory; M3 is implemented with 29 local backend tests, but API role/negative, frontend, and E2E coverage remain open before acceptance.

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
- **Current backend evidence (M3):** `ruff check apps config`, `manage.py check`, `makemigrations --check --dry-run`, `pytest -q` (**29 passed**) against PostgreSQL 18; migration application verified. Coverage is mostly service/workflow-level; API role/negative tests are still required for M3 acceptance.

### 2.2 Frontend (Vitest/React Testing Library as chosen)
- Component/unit tests for critical UI logic and rendering states.
- Form validation and submission behavior (RHF/Zod schemas aligned with API).
- Routing/protected-route and role-based UI visibility (non-authoritative) tests.
- API client/error/loading/empty-state handling.
- Accessibility checks (automated tooling e.g. axe where integrated) for key screens/components.

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
- E2E: run in CI on staging-like environment or nightly/per-release suite as feasible.
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

*Tooling choices (pytest plugins, coverage tools, Vitest config, Playwright) to be finalized in Technology Compatibility/implementation setup and recorded in CI config.*
