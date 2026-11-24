# Entity Relationship Diagram

**Status:** Living ER model. M1/M2 entities are implemented; M3 academic/teaching/attendance and M4 examinations/results/report-card/transcript/alumni entities are implemented locally with the listed hardening gaps closed. M3/M4 are accepted with formal UAT/sign-off recorded and Q-003 confirmed (D-032); remaining Phase 4+ entities are blueprint-only.
**Notation:** textual ER model (entities, key attributes, relationships). A visual diagram should be produced during implementation (e.g. dbdiagram/ERD tool) once reviewed.

## 1. Conventions
- **Internal PK:** `id` (UUID recommended) for most entities.
- **Scoping:** most institution-owned records include `institution_id` (FK) and, where relevant, `campus_id` (FK). Enforce in queries/services.
- **Audit fields (common):** `created_at`, `updated_at`, and where appropriate `created_by`, `updated_by`, `is_active`/status, soft-archive flags (never for immutable official/posted records—use reversals/versions).
- **History/versioning:** effective-dated or versioned records for allocations, grading schemes, results corrections, transcripts, policies where required.
- **Uniqueness:** DB-level unique constraints for official human-readable identifiers per defined scope.

## 2. Core Domains & Entities

### 2.1 Institutions & Configuration
- **Institution** (`id`, name, code, settings, branding refs, is_active)
- **Campus** (`id`, institution_id FK, name, code, address, is_active)
- **InstitutionSetting/BrandSetting** (`institution_id`, keys for locale/timezone/currency/date-format, logos/colors/theme, report branding)
- Relationships: Institution 1—N Campus.

### 2.2 Accounts, Permissions, Audit
- **User** (`id`, institution_id, email/username, password_hash, is_active, last_login, etc.)
- **Role** (`id`, institution_id nullable-if-global-template, name, description, configurable)
- **Permission** (`id`, code, module/action/resource)
- **RolePermission** (`role_id`, `permission_id`, scope rules)
- **UserRole** (`user_id`, `role_id`, scope: institution/campus/class/subject/record/own, effective dates)
- **AuditLog** (immutable: `id`, actor_user_id, action, target_type/id, institution_id, campus_id?, timestamp, reason?, change_summary/safe diff metadata, metadata, ip_address, `sequence_number`, `previous_hash`, `entry_hash`)
- Relationships: User N—M Role via UserRole; Role N—M Permission via RolePermission; actions produce AuditLog. Per-scope sequence/hash chain is verified by `verify_audit_chain`; PostgreSQL triggers reject AuditLog UPDATE/DELETE.

### 2.3 People: Students, Guardians, Employees (Employees M3)
- **Student** (`id`, institution_id, campus_id current, admission_number [unique scoped], internal_ref, biodata, photo, status/lifecycle_state, admission_date, current_enrolment refs)
  - **StudentLifecycleHistory** (`student_id`, from_state, to_state, effective_at, reason, actor_id)
  - **StudentDocument** (`student_id`, type, file_ref, metadata, visibility)
- **Guardian** (`id`, institution_id, names, contacts, address, preferences/consent)
- **StudentGuardian** (`student_id`, `guardian_id`, relationship, is_primary, financial_responsibility, authorized_pickup, portal_access)
- **Employee** (`id`, institution_id, campus_id, employee_number [unique scoped], user_id nullable, biodata, department, job_title, employment_type/status)
- Relationships: Student N—M Guardian; Employee optionally 1—1 User. Stable identities preserved across lifecycle.

### 2.4 Admissions
- **Enquiry** (`id`, institution_id, campus_id, applicant details, intended class, source, status, follow-ups)
- **Application** (`id`, institution_id, campus_id, applicant/student link, cycle, intended class/arm, status, submitted_at)
- **ApplicationDocument** (`application_id`, checklist item, file_ref, review_status)
- **AdmissionDecision** (`application_id`, outcome, decided_by, decided_at, notes)
- Relationships: Application may convert/link to Student (no duplicate identity); audit on decisions.

### 2.5 Academics & Teaching (M3 slice implemented)
- **AcademicSession** (`id`, institution_id, name, start/end, is_current/closed)
- **Term** (`id`, session_id, name/order, start/end, status)
- **ClassLevel** (`id`, institution_id/campus scope as configured, name/grade, level band nursery/primary/secondary)
- **Arm/Section** (`id`, class_level_id, campus_id?, name)
- **Subject** (`id`, institution_id, code, name, description, status)
- **SubjectOffering** (`id`, subject_id, session_id/term_id?, class_level_id, arm_id?, compulsory/optional, effective dates)
- **ClassEnrolment** (`id`, student_id, session_id, term_id?, class_level_id, arm_id, campus_id, status, effective dates) — historical
- **Timetable** (`id`, scope session/term/class/arm, version/status)
- **TimetableSlot** (`timetable_id`, day, period, subject_offering, room/venue?, employee?, teacher_assignment?)
- **TeacherAssignment** (`id`, institution_id, campus_id, session_id, term_id?, class_level_id, arm_id, offering_id, employee_id/teacher, role [lead/assistant/substitute], workload_hours, start/end, status, authorized_by)
- **TeacherWorkloadPolicy** (`id`, institution_id, campus_id?, name, effective_from/to, max_hours, is_active)
- **Timetable** also carries `revision_of`, `approved_by/at`, `published_by/at`; **TimetableSlot** carries `recurrence`, `recurrence_interval`, `recurrence_until`.
- Relationships: Session 1—N Term; ClassLevel 1—N Arm; SubjectOffering links Subject to Class/Arm/period; TeacherAssignment links Employee to Subject/Class/Arm (historical, auditable); workload is resolved from the effective institution-scoped policy; recurring timetable slots enforce add-time teacher/class/room conflict checks, with draft/approve/publish/revise versions.

### 2.6 Attendance (M3 implemented locally)
- **AttendanceSession** (`id`, institution_id, campus_id, subject_offering, date, status, opened_by/closed_by/timestamps) — period-level sessions remain planned
- **AttendanceRecord** (`attendance_session_id`, student, status [present/absent/late/excused], marked_by, marked_at, correction_count)
- **TeacherAttendanceRecord** (`id`, institution_id, campus_id, employee_id, attendance_date, status, approval_status, marked_by, approved_by/at)
- **AttendanceCorrection** (`attendance_record_id`, previous_status, new_status, reason, requested_by, approved_by)
- Relationships: auditable student corrections and teacher attendance marking/approval; summaries/exports remain planned.

### 2.7 Examinations, Results, Report Cards (M4 implemented locally)
- **AssessmentScheme** (`id`, institution_id, level/scope, session/term, effective dates, grading config ref) — preserved historically
- **AssessmentComponent** (`scheme_id`, type [CA/test/exam/etc], name, max_marks, weight, applicable scope)
- **GradingScale** (`id`, institution_id, name, effective dates, boundaries/grade/description/remarks/gpa rules as configured)
- **GradingPolicy** (`id`, institution_id, campus_id?, grading_scale_id, effective dates, result_completeness_rules, report_card_settings, is_active) — configurable effective-dated policies accepted as institutional baseline (Q-003/D-032)
- **ResultRecord** (`id`, student_id, subject_offering_id, session_id, term_id, component scores, total, grade, computed fields metadata, status [draft/submitted/returned/resubmitted/approved/published])
- **ResultWorkflowAction** (`result_record_id` or batch, action, actor_id, timestamp, comments)
- **ResultCorrection** (`result_record_id`, original_values, revised_values, reason, requester, reviewer, approver, timestamps, prior_version_ref)
- **ReportCard** (`id`, institution_id, campus_id?, student_id, session_id, term_id, reference, version, status, template_version, results_snapshot, document_snapshot, private `file`/file_ref, content_type, size_bytes, pdf_sha256, generated_by, published_at)
- Relationships: ResultRecord unique per student/offering/scheme; ResultWorkflowAction records each transition; ResultCorrection preserves prior scores/total/grade with reason; only published results feed ReportCard and Transcript JSON snapshots; PDF report cards use private storage/hash with authenticated download. Ranking, attempts, and promotion feature implementation remains blueprint-only; Q-003 policy confirmation is accepted (D-032).

### 2.8 Transcripts & Alumni (M4 implemented locally)
- **TranscriptRequest** (`id`, institution_id, campus_id?, student_id, requested_by, purpose, requested_kind [provisional/official], status [requested/under_review/approved/rejected/generated/issued], decision_reason, reviewed_by/approved_by, reviewed_at/approved_at)
- **Transcript** (`id`, institution_id, campus_id?, student_id, request_id, supersedes_id?, reference_number [unique per institution], version, kind [provisional/official], status [generated/issued/corrected/superseded/revoked], verification_token_hash [unique], verification_token_issued_at, verification_revoked_at, file/file_ref, content_type, size_bytes, pdf_sha256, template_version, issued_to, issue_purpose, issued_by/approved_by, issued_at, document_snapshot, results_snapshot, completeness)
- **TranscriptEvent** (`request_id?`, `transcript_id?`, action, from_status, to_status, actor_id, reason)
- **TranscriptVerification** (`transcript_id?`, token_hash, outcome [valid/invalid/revoked/superseded/invalid_state], checked_at)
- **AlumniRecord** (`id`, institution_id, campus_id?, student_id [unique link], graduation_event_id [unique link to StudentLifecycleEvent], graduation_date, graduation_reference) — implemented in `apps.alumni`
- Relationships: one `TranscriptRequest` may produce multiple versioned `Transcript` rows; `supersedes` links corrections to prior transcripts; transcript snapshots preserve published results and historical grading content; verification logs every token check; graduation links Student 1—0..1 AlumniRecord. Full alumni engagement/profile/portal fields remain blueprint-only.

### 2.9 Finance (MVP)
- **FeeCategory** (`id`, institution_id, name, type)
- **FeeSchedule** (`id`, institution_id, campus_id?, session_id, term_id?, class_level_id?, items, amounts, currency [NGN default], compulsory/optional, due dates)
- **Invoice** (`id`, institution_id, student_id, invoice_number [unique], session/term, currency, total, status, due_date)
- **InvoiceLine** (`invoice_id`, fee_category/schedule ref, description, amount, discount/waiver refs)
- **Payment** (`id`, institution_id, student_id?, invoice_id(s) via allocation, receipt_number [unique], amount, currency, method, provider ref, status, verified_at)
- **PaymentAllocation** (`payment_id`, `invoice_id`, amount)
- **FinancialAdjustment** (`id`, type [refund/reversal/credit/waiver], related payment/invoice, amount, reason, authorized_by, status) — no deletion of posted txns
- Relationships: auditable, idempotent payment posting; server-verified gateway events.

### 2.10 Inventory, Procurement, Asset Management
- **Item** (`id`, institution_id, sku/code [unique scoped], name, category, unit, type [consumable/stock/non-stock/asset-controlled], reorder levels)
- **StoreLocation** (`id`, institution_id, campus_id, name)
- **StockMovement** (`id`, item_id, store_id, type [receipt/issue/transfer/return/adjustment/opening], qty, ref (GRN/issue/transfer), actor, reason, timestamp) — ledger; balances derived/maintained transactionally
- **StockCount/Reconciliation** (`id`, store_id, date, lines, variances, approvals)
- **Supplier** (`id`, institution_id, details, status)
- **PurchaseRequisition** (`id`, number, requester/dept, items, status/approvals)
- **PurchaseOrder** (`id`, number, supplier_id, items, status/approvals/amendments)
- **GoodsReceivedNote** (`id`, number, po_id, accepted/rejected/damaged qtys)
- **SupplierInvoiceMatch** (`id`, supplier invoice ref, po_id, grn_id, status)
- **Asset** (`id`, institution_id, campus_id, asset_number/tag [unique], item/category, serial/barcode, acquisition/cost, location, custodian employee_id, condition, status, warranty/insurance refs)
- **AssetHistory** (`asset_id`, event [register/assign/return/transfer/maintenance/verify/dispose], from/to, actor, dates, notes)
- Relationships: PO may contain stock and/or asset lines; receipts route to stock movements or asset records; traceability req→PO→GRN→movement/asset→supplier invoice→payment.

### 2.11 Identity Cards
- **IdCardTemplate** (`id`, institution_id, campus_id?, type [student/staff], layout/branding config, version)
- **IdCard** (`id`, holder_type/id [student/employee], template_id/version, card_number/ref, status [draft/generated/approved/issued/active/expired/revoked/replaced], issue/expiry dates, verification_token, issued_by/approved_by, previous_card_id?)
- **IdCardEvent** (`id_card_id`, action, reason, actor, timestamp)
- QR encodes non-guessable verification token only (no sensitive biodata).

### 2.12 CMS & Communications
- **CmsPage** (`id`, institution_id, slug, title, content blocks, status [draft/review/published/archived], publish schedule, seo/meta, revision refs)
- **CmsMenu/NavItem**, **CmsMedia** (public), **CmsPost/Event/GalleryItem** (published/public fields only)
- **NotificationTemplate**, **Notification/MessageLog** (`channel`, target, status, retries/failures, consent/context)

## 3. Key Integrity & Scoping Notes
- All institution-owned records carry `institution_id`; campus-scoped records carry `campus_id`; enforce in all access paths.
- No duplicate student/person identities across admissions→student→alumni.
- Historical/approved academic & financial records are immutable in effect (version/correct/reverse, never destructive overwrite/delete).
- Official IDs (admission, employee, invoice, receipt, transcript ref, asset tag, PO/GRN/requisition numbers, etc.) unique per defined scope and immutable once issued except controlled correction.

## 4. Implemented migration evidence (through M4 closure)
- M1: `accounts`, `institutions`, `permissions`, `audit`.
- M2: `admissions`, `guardians`, `students`, `documents`, `imports`, identifier sequences/lifecycle history.
- M3: `employees/0001_initial.py`, `academics/0001_initial.py`, `teaching/0001_initial.py` + `teaching/0002_m3_workload_recurrence_publish.py`, `attendance/0001_initial.py` + `attendance/0002_m3_teacher_attendance.py`, permission seed `permissions/0004_seed_phase3_permissions.py`, and `permissions/0007_normalize_role_names.py`.
- M4: `examinations/0001_initial.py` + `examinations/0002_m4_report_card_pdf_and_grading_policy.py`, `transcripts/0001_initial.py`, `alumni/0001_initial.py`, `audit/0002_auditlog_immutability_chain.py`, permission seeds `permissions/0005_seed_phase4_permissions.py`, `permissions/0006_seed_phase4_transcript_permissions.py`, and `permissions/0008_seed_alumni_permissions.py`.
- Migration state validated locally with `python manage.py makemigrations --check --dry-run` and `pytest -q` (68 passed) against PostgreSQL 18. M3/M4 technical gaps are closed locally and M3/M4 are accepted with formal UAT/sign-off recorded and Q-003 confirmed (D-032); promotion/attempt feature implementation remains blueprint-only.

*This ER model is a living blueprint refined with migrations; final schema/MRD continues to be validated during implementation.*
