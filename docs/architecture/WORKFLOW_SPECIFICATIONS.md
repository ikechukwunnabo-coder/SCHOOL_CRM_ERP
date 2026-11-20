# Workflow Specifications

**Status:** Draft (documented, not implemented). Workflows must be enforced by backend services/state machines with transactions and audit logs.

## 1. Admissions & Enrolment
- **States (configurable):** `Enquiry → Application Started → Submitted → Under Review → Assessment/Interview → Approved → Offered → Accepted → Enrolled`; alt: Rejected, Withdrawn, Waitlisted, Deferred.
- **Key steps:** capture enquiry/applicant & guardian info; configurable form/checklist; document upload/review; decision & approval record; offer/acceptance tracking.
- **Conversion:** accepted applicant → create/link **Student** without duplicate identity; generate admission number (configurable pattern, DB-unique scoped).
- **Controls:** validate transitions; audit who/when/why; permissions per admissions roles.

## 2. Student Lifecycle
- **States:** `Applicant → Admitted → Enrolled → Active → Promoted / Repeated / Transferred / Withdrawn / Graduated` (+ Alumni linkage).
- **Transitions:** promotion (individual/batch), repetition, transfer (campus/class/arm), withdrawal, graduation, re-admission (preserve original identity/history; new enrolment period as appropriate).
- **Rules:** no deletion of academic/financial history; record actor/effective date/reason; withdrawal does not erase obligations; graduation preserves complete academic record and triggers/links AlumniProfile (no duplicate person).

## 3. Subject–Teacher Allocation & Teaching
- **Setup:** admin configures subjects/offerings per class/arm/session/term; creates TeacherAssignment (employee, subject, class, arm, session/term, role lead/assistant/substitute, workload, effective dates, status).
- **Validations:** detect timetable/teacher/class/room conflicts and workload limits (configurable); support reassignment/substitution with history.
- **Authority:** subject teacher acts only on assigned scopes; class teacher has class overview (not blanket mark-edit rights) unless separately authorized. All allocation changes audited.

## 4. Attendance
- **Capture:** daily and/or lesson/period-based; by class/arm (and subject/period if configured); statuses present/absent/late/excused/approved leave.
- **Corrections:** authorized correction with mandatory reason; preserve previous value; audit actor/time.
- **Outputs:** summaries by student/class/term/session; notifications per config; reports/export. (Biometric integration deferred.)

## 5. Examinations, Results & Publication
- **Configuration:** assessment schemes/components (CA/tests/exam/practical etc.), max marks/weights, dates, applicable scope, grading scale effective-dated per level/period. No hardcoded universal structure.
- **Entry:** assigned subject teacher enters marks (draft/bulk) for assigned scope only; validate ranges/max; detect missing/invalid; prevent duplicates per student/subject/assessment/period unless attempts allowed; record user/timestamps.
- **Workflow:** `Draft → Submitted → Returned for Correction → Resubmitted → Approved → Published` (stages configurable, permissions/audit enforced).
  - Teachers cannot self-approve unless explicitly permitted.
  - Published/approved results **not** silently edited.
- **Post-approval correction:** formal correction request → record reason, original vs revised, requester/reviewer/approver/timestamps; recalc totals/grades/positions/report cards via controlled services; preserve prior published versions.
- **Calculation:** configurable weighting, totals, grade boundaries/descriptions/remarks, averages, ranking/positions (if enabled), promotion eligibility; documented rounding/tie rules.

## 6. Report Cards
- **Source:** approved & published results only (never draft/unapproved).
- **Generation:** per term/session for individual or authorized bulk; configurable branded template (school/student identity, subjects/scores/grades/breakdown, attendance summary, remarks/signatures, grading legend, promotion status if applicable, rank if enabled).
- **Output/controls:** PDF; record generation/publication events; restrict access to authorized users/parent/student.

## 7. Cumulative Transcripts
- **Source:** approved & published historical results across sessions/terms; preserve grading scheme effective at time earned (no retroactive recalculation under new scales).
- **Request/issue workflow:** `Requested → Under Review → Approved → Generated → Issued` (corrections via separate authorized process).
- **Content:** institution/student identity, admission/graduation dates, classes/sessions/terms/subjects/scores/grades, cumulative averages/GPA only if validly defined, status, unique reference, signatory/issue date, verification (QR/secure URL/token).
- **Rules:** unique reference; printable PDF; record every issuance (by/to/when/purpose); reissue/correction preserves prior issue/version history; provisional labeling or block if incomplete per policy; verification exposes minimal non-sensitive data (no sensitive biodata in QR).
- **Access:** expiring/access-controlled download links for private documents.

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
