# API Design

**Status:** Living API design. M1–M3 endpoints and the M4 examinations backend endpoints are implemented and evidenced; remaining Phase 4+ groups stay illustrative until coded. M3 and M4 are implemented but not accepted.
**Style:** RESTful JSON APIs (Django REST Framework), versioned, with generated schema at `/api/schema/` and Swagger UI at `/api/docs/`.

## 1. Conventions
- **Base path & versioning:** `/api/v1/` (versioned to allow evolution). Public CMS read endpoints may be namespaced (e.g. `/api/v1/public/`) and strictly limited to published content.
- **Resources:** plural nouns, hierarchical where clear (e.g. `/students/{id}/guardians`, `/sessions/{id}/terms`, `/invoices/{id}/payments`). Use filters for cross-cutting queries.
- **Methods:** `GET` read, `POST` create/action, `PATCH` partial update, `PUT` replace only if needed, `DELETE` archive/disable where allowed (prefer state transitions for official records; never hard-delete immutable/posted/official data).
- **IDs:** UUIDs for resource identifiers in URLs; human-readable official numbers as attributes.
- **Response envelope (consistent):** e.g. `{ "data": ..., "meta": {...} }` for single/collection and `{ "errors": [...] }` for failures; finalize shape in implementation (consistency over specific form).

## 2. Authentication & Authorization
- **Auth (recommended/pending D-011):** HttpOnly/Secure/SameSite cookies with CSRF protection for state-changing requests; login/logout, password reset (time-limited single-use tokens), throttling. Alternative token approach must include rotation/revocation and secure storage (no long-lived tokens in localStorage).
- **Auth endpoints (examples):** `POST /auth/login`, `POST /auth/logout`, `POST /auth/password-reset/request`, `POST /auth/password-reset/confirm`, `GET /auth/me`, session/refresh as applicable.
- **Authorization:** deny-by-default, enforced server-side on every endpoint and queryset (institution, campus, role/scope, record/object-level). 401 unauthenticated, 403 unauthorized; do not leak existence of out-of-scope resources where sensitive (prefer 404/403 per policy consistently).
- **RBAC checks:** permission codes/scopes per `RBAC_PERMISSION_MATRIX.md`; scoped to institution/campus/class/subject/record/own.

## 3. Multi-tenancy / Scoping
- Institution context resolved from authenticated user/session (and/or explicit header/path where designed) and **always enforced server-side**.
- Campus scoping applied where relevant; list endpoints filtered by authorized scopes by default.
- Prevent cross-institution/cross-campus access in views, serializers, services, and background jobs.

## 4. Pagination, Filtering, Sorting, Search
- **Pagination:** cursor or page-number pagination for collections (default & max page size enforced) to protect large datasets.
- **Filtering:** query params for common fields (e.g. `session`, `term`, `campus`, `class`, `arm`, `status`, `date_from/date_to`) with validated whitelists.
- **Sorting:** `ordering`/`sort` param with allowed fields only.
- **Search:** limited full-text/substring search on indexed fields where appropriate.

## 5. Validation & Error Handling
- **Validation:** server-side authoritative (DRF serializers + model/service validation); clear, field-level error messages; reject invalid state transitions and out-of-range marks/scores/quantities.
- **Standard HTTP codes:** 200/201 success, 204 no content, 400 validation, 401 unauth, 403 forbidden, 404 not found, 409 conflict (duplicates/state/idempotency), 422 if used consistently, 429 throttled, 5xx server errors.
- **Error format:** consistent structure with code, message, and field errors (no sensitive/internal details leaked).
- **Idempotency:** required for payment callbacks/webhooks and critical create/post operations (idempotency keys) to prevent duplicates.

## 6. Domain Endpoint Groups (illustrative, non-exhaustive)

| Group | Examples | Notes |
|---|---|---|
| Auth/Accounts | `/auth/*`, `/users`, `/roles`, `/permissions` | admin/scoped management; self profile limited |
| Institutions/Config | `/institutions`, `/campuses`, `/settings`, branding | scoped admin |
| Admissions | `/enquiries`, `/applications`, `/applications/{id}/submit|decide|convert` | workflow actions as explicit endpoints |
| Students/Guardians | `/students`, `/students/{id}/lifecycle`, `/guardians`, `/students/{id}/guardians`, documents | conversion preserves identity; history read |
| Employees | `/employees`, departments/positions | base HR; payroll R2 |
| Academics | `/sessions`, `/terms`, `/classes`, `/arms`, `/subjects`, `/offerings`, `/enrolments` | historical structures |
| Teaching/Timetable | `/teacher-assignments`, `/timetables`, `/timetable-slots` | conflict validation |
| Attendance | `/attendance-sessions`, `/attendance-records`, `/attendance-records/{id}/corrections` | corrections audited |
| Examinations/Results | `/assessment-schemes`, `/components`, `/grading-scales`, `/results`, `/results/{id}/submit|review|approve|publish`, `/results/{id}/corrections` | scoped to assigned teacher; controlled workflow |
| Report Cards | `/report-cards/generate`, `/report-cards/{id}` (PDF/download) | approved/published data only; authorized access |
| Transcripts | `/transcript-requests`, `/transcripts`, `/transcripts/{id}/issue|correct`, `/transcripts/verify/{token}` | verify returns minimal public info |
| Finance | `/fee-categories`, `/fee-schedules`, `/invoices`, `/payments`, `/receipts`, `/adjustments`, `/webhooks/payments/{provider}` | server-verified payments, idempotent, signed webhooks |
| Inventory/Procurement/Assets | `/items`, `/stores`, `/stock-movements`, `/stock-counts`, `/suppliers`, `/requisitions`, `/purchase-orders`, `/grns`, `/assets`, `/assets/{id}/history` | transactional movements; controlled adjustments |
| ID Cards | `/id-card-templates`, `/id-cards/generate`, `/id-cards/bulk-generate`, `/id-cards/{id}/approve|issue|revoke|replace`, `/id-cards/verify/{token}` | limited verification response |
| CMS (admin) & Public | `/cms/pages`, `/cms/media`, `/cms/menus`, `/cms/posts|events|gallery`; `/public/*` read-only published | strict separation from private ERP |
| Communications | `/notifications`, `/templates`, `/announcements`, delivery logs | consent/preferences aware |
| Reports/Exports | `/reports/*`, `/exports` (async status/download) | scoped, logged; async for large jobs |
| Audit | `/audit-logs` (read-only, restricted) | immutable |

### 6.1 Implemented endpoints (M1–M4 backend)
| Area | Concrete paths | Notes |
|---|---|---|
| Auth/health | `/api/v1/health/`, `/api/v1/auth/csrf|login|logout|me/` | session + CSRF auth; schema/docs at `/api/schema/`, `/api/docs/` |
| Institutions | `/api/v1/institutions/`, `/api/v1/campuses/` | institution/campus scoped reads |
| Admissions/students/imports | `/api/v1/admissions/...`, `/api/v1/students/...`, `/api/v1/imports/...` | M2 workflow and controlled import endpoints |
| Employees | `/api/v1/employees/` | M3 employee records |
| Academics | `/api/v1/academic-sessions/`, `/api/v1/terms/`, `/api/v1/class-levels/`, `/api/v1/arms/`, `/api/v1/subjects/`, `/api/v1/subject-offerings/`, `/api/v1/class-enrolments/` | M3 structure; standard router CRUD |
| Teaching | `/api/v1/teacher-assignments/`, `/api/v1/teacher-assignments/my-assignments/`, `/api/v1/teacher-assignments/{id}/reassign/`, `/api/v1/timetables/`, `/api/v1/timetable-slots/`, `/api/v1/timetables/{id}/add-slot/` | effective-dated assignments, reassignment history, draft/versioned timetable conflict checks |
| Attendance | `/api/v1/attendance-sessions/`, `/api/v1/attendance-sessions/open/`, `/api/v1/attendance-sessions/{id}/mark/`, `/api/v1/attendance-sessions/{id}/expected-students/`, `/api/v1/attendance-sessions/{id}/close/`, `/api/v1/attendance-sessions/{id}/correct/`, `/api/v1/attendance-records/`, `/api/v1/attendance-corrections/` | student offering-based attendance; corrections require reason and privileged grant |
| Examinations | `/api/v1/examinations/assessment-schemes/`, `/api/v1/examinations/assessment-components/`, `/api/v1/examinations/grading-scales/`, `/api/v1/examinations/results/`, `/api/v1/examinations/results/submit/`, `/api/v1/examinations/results/{id}/return-for-correction|approve|publish|correct/` | configurable assessment/grading, weighted scoring, controlled workflow, correction history |
| Report cards | `/api/v1/examinations/report-cards/`, `/api/v1/examinations/report-cards/generate/` | published-only snapshots; PDF download not implemented |

M3 caveats: `my-assignments` is the only teacher-scoped list endpoint; other queryset scoping is service-level/institution-level. M4 includes API role/negative tests for approval/publication; frontend/E2E integration and PDF/download endpoints remain open.

## 7. File Uploads & Downloads
- Multipart uploads with validation (type/size/MIME/extension, safe names); malware-scan hook where available.
- Private documents served via authenticated endpoint or short-lived signed URLs after authorization check; public CMS media via controlled public storage/CDN paths only.

## 8. Async & Webhooks
- Long-running operations (bulk generate, exports, large reports) return job/task IDs with status polling endpoints.
- Webhooks: verify signatures, enforce idempotency, record events, reconcile asynchronously; return fast 2xx on accepted valid events.

## 9. Documentation & Testing
- OpenAPI schema is generated at `/api/schema/` with Swagger UI at `/api/docs/`; add examples for critical workflows.
- M1–M3 have local service/workflow tests; M4 adds service tests plus API role/negative tests for result approval/publication. Frontend/E2E and contract coverage for validation/idempotency remain outstanding.
- Remaining Phase 4 endpoint paths/names (transcripts, verification, graduation/alumni) are illustrative; finalize during implementation with consistent naming and OpenAPI review.
