# Workflow Specifications

**Status:** Living workflow specification. M1–M2 workflows are implemented; M3 academic/teaching/attendance workflows and the M4 examinations/results/report-card/transcript backend workflows are implemented as open hardening slices. Workflows are enforced by backend services with transactions and application-level audit logs; remaining Phase 4+ items remain blueprint-only.

## 1. Admissions & Enrolment (M2 implemented)
- **States (configurable):** `Enquiry → Application Started → Submitted → Under Review → Assessment/Interview → Approved → Offered → Accepted → Enrolled`; alt: Rejected, Withdrawn, Waitlisted, Deferred.
- **Key steps:** capture enquiry/applicant & guardian info; configurable form/checklist; document upload/review; decision & approval record; offer/acceptance tracking.
- **Conversion:** accepted applicant → create/link **Student** without duplicate identity; generate admission number (configurable pattern, DB-unique scoped).
- **Controls:** validate transitions; audit who/when/why; permissions per admissions roles.

## 2. Student Lifecycle (M2 implemented)
- **States:** `Applicant → Admitted → Enrolled → Active → Promoted / Repeated / Transferred / Withdrawn / Graduated` (+ Alumni linkage).
- **Transitions:** promotion (individual/batch), repetition, transfer (campus/class/arm), withdrawal, graduation, re-admission (preserve original identity/history; new enrolment period as appropriate).
- **Rules:** no deletion of academic/financial history; record actor/effective date/reason; withdrawal does not erase obligations; graduation preserves complete academic record and triggers/links AlumniProfile (no duplicate person).

## 3. Subject–Teacher Allocation & Teaching (M3 slice implemented; hardening open)
- **Setup:** admin configures academic sessions/terms, class levels/arms, subjects/offerings, class enrolments, and effective-dated teacher assignments.
- **Validations:** timetable creation and `add-slot` reject teacher/class/room conflicts for the same session/term/day/period; reassignment preserves history. Workload is currently a hard-coded 40-hour cap and must become configurable before M3 acceptance.
- **Authority:** `my-assignments` returns the acting teacher's assignments; assignment and audit service methods use teacher scope. Recurring timetable rules, publish/version approval, and API-level cross-scope denial tests are not yet implemented.

## 4. Attendance (M3 slice implemented; hardening open)
- **Capture:** implemented student attendance sessions tied to a subject offering and date, with `open`, `expected-students`, `mark`, and `close` actions; statuses present/absent/late/excused. Period-level capture, teacher attendance, notifications, and summaries/exports remain planned.
- **Corrections:** privileged `correct` action requires a reason, stores a separate correction record, and writes application-level audit events.
- **Scope:** teacher assignment checks are service-level; broader queryset-scope enforcement and API role/negative tests remain open.

## 5. Examinations, Results & Publication (M4 backend slice implemented; hardening open)
- **Implemented backend:** assessment schemes/components with max marks/weights and effective dates; effective-dated grading scales with configurable grade ranges/remarks; offering-scoped result entry with weighted score calculation; `submit`, `return-for-correction`, `approve`, `publish`, and `correct` services; correction history and re-approval; self-approval denial; application-level audit events.
- **Configuration:** assessment schemes/components (CA/tests/exam/practical etc.), max marks/weights, dates, applicable scope, grading scale effective-dated per level/period. No hardcoded universal structure.
- **Entry:** assigned subject teacher enters marks (draft/bulk) for assigned scope only; validate ranges/max; detect missing/invalid; prevent duplicates per student/subject/assessment/period unless attempts allowed; record user/timestamps.
- **Workflow:** `Draft → Submitted → Returned for Correction → Resubmitted → Approved → Published` (stages configurable, permissions/audit enforced).
  - Teachers cannot self-approve unless explicitly permitted.
  - Published/approved results **not** silently edited.
- **Post-approval correction:** formal correction request → record reason, original vs revised, requester/reviewer/approver/timestamps; recalc totals/grades/positions/report cards via controlled services; preserve prior published versions.
- **Calculation:** configurable weighting, totals, grade boundaries/descriptions/remarks, averages, ranking/positions (if enabled), promotion eligibility; documented rounding/tie rules. Current backend implements weighted totals and grade/remark lookup only; ranking and promotion policy remain pending.

## 6. Report Cards (M4 backend snapshot implemented; PDF/portals pending)
- **Source:** approved & published results only (never draft/unapproved). Current backend generates immutable-style JSON snapshots from published results and increments version on regeneration.
- **Generation:** per term/session for individual or authorized bulk; configurable branded template (school/student identity, subjects/scores/grades/breakdown, attendance summary, remarks/signatures, grading legend, promotion status if applicable, rank if enabled).
- **Output/controls:** PDF; record generation/publication events; restrict access to authorized users/parent/student.

## 7. Cumulative Transcripts (M4 backend slice implemented; hardening open)
- **Source:** published historical results across sessions/terms; `build_transcript_snapshot` copies grading-scale grades, component scores, and result metadata at generation time (no retroactive recalculation under later scales).
- **Request/issue workflow:** `Requested → Under Review → Approved/Rejected → Generated → Issued`; self-approval is denied; issue requires recipient, purpose, and `issue_or_revoke` permission.
- **Content:** institution/student identity, admission/graduation dates, classes/sessions/terms/subjects/scores/grades, completeness flags, status, unique reference, version/kind, issue date/actor/recipient/purpose, verification path with QR/token.
- **Rules:** unique institution-scoped reference; private printable PDF; every transition is audited via `TranscriptEvent`; correction creates a new version/token/reference/PDF and marks the prior transcript `SUPERSEDED`; revocation invalidates verification; provisional labeling is used for incomplete records and official generation is blocked by default (`institution.settings.transcript_block_incomplete_official`) unless policy allows it.
- **Verification:** public `POST /api/v1/transcripts/verify/` hashes the submitted token, records a `TranscriptVerification` outcome (`valid`, `invalid`, `revoked`, `superseded`, `invalid_state`), and returns minimal document status/metadata with no student personal data.
- **Access:** authenticated private-document download endpoint with RBAC/institution/campus checks; short-lived signed URLs remain a future option.

## 8. Finance (MVP: Fees, Invoices, Payments)
- **Setup:** fee categories/schedules by class/campus/session/term; compulsory/optional; discounts/scholarships/bursaries; installments; due dates; authorized waivers/adjustments.
- **Invoicing:** generate invoices/lines, student statements; track status (issued/part-paid/paid/void-controlled).
- **Payments:** full/partial payments, methods, receipts, allocation to invoices, overpayments/credit; server-side gateway verification & authenticated callbacks/webhooks; idempotency to prevent duplicates; **never** mark paid on client redirect; store currency (NGN default).
- **Refunds/reversals/adjustments:** controlled, authorized workflows with audit trail; **no deletion** of posted financial transactions.
- **Reconciliation/reporting:** outstanding/ageing, exports; design integration point for R2 double-entry GL (do not mislabel basic tracking as full accounting).

## 9. Procurement, Inventory & Asset Management
- **Procurement:** `Purchase Requisition → Dept Review → Budget/Finance Check → Approval → RFQ (if required) → Supplier Selection → PO → Goods Received → Invoice Matching → Payment Processing`. Controls: approval limits, segregation of duties (configurable), no self-approval where enabled, partial deliveries/backorders, three-way match evidence, audit.
- **Inventory (stock):** catalog/stores; opening/receipt (GRN-linked) → issue/requisition → transfers → returns → adjustments (reason+approval) → counts/reconciliation. Ledger of movements; transactional updates; no unapproved negative stock.
- **Assets:** `Requested → Procured → Received/Registered → Available → Assigned → Under Maintenance/Returned/Transferred → Retired/Disposed`. Serialized register, tagging, custody/assignment history, maintenance/warranty, verification, authorized write-off/disposal.
- **Integration:** PO lines route to stock receipt or asset registration by type; traceability req→PO→GRN→movement/asset→invoice→payment; finance records liabilities/payments without conflicting ledger.

## 10. Identity Cards (Student & Staff)
- **Data source:** auto-populated from existing student/employee biodata (no re-entry).
- **Lifecycle:** `Draft → Generated → Approved → Issued → Active → Expired / Revoked / Replaced`.
- **Generation/print:** individual & bulk (by class/arm/campus/dept/category); configurable templates (student/staff, front/back, branding/fields, CR80 or configured, A4 sheets), PDF print-ready, preview/reprint.
- **Verification:** unique QR with non-guessable token → secure endpoint showing limited approved status info only (no sensitive biodata in QR/response beyond policy); expired/revoked not shown active.
- **Controls:** issuance/replacement/revocation history, prevent duplicate active cards per policy, RBAC & audit on all operations.

## 11. CMS / Public Website Publishing
- **Workflow:** draft → review → publish (and schedule/unpublish/archive) with revision history.
- **Scope:** pages, menus, news/events/gallery, SEO/meta/redirects, approved public profile fields only.
- **Controls:** role-based CMS permissions; **no exposure** of private ERP/student/staff/financial records via public endpoints; explicit publication status and field whitelisting.

## 12. Communications & Notifications
- **Flow:** compose/select template → target by role/campus/class/parent/student → schedule/send → log delivery status/retries/failures.
- **Controls:** consent/preferences; avoid sensitive data in insecure channels (link to authenticated portal where appropriate); audit important communications.

*Each workflow to be modeled with explicit state diagrams, permissions per transition, validation rules, and compensating/rollback behavior during detailed design.*
