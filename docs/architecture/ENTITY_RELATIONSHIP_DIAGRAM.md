# Entity Relationship Diagram

**Status:** Living ER model. M1/M2 entities are implemented; M3 academic/teaching/attendance entities are implemented as an open hardening slice; Phase 4+ entities remain blueprint-only.
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
- **AuditLog** (immutable: `id`, actor_user_id, action, target_type/id, institution_id, campus_id?, timestamp, reason?, change_summary/safe diff metadata)
- Relationships: User N—M Role via UserRole; Role N—M Permission via RolePermission; actions produce AuditLog.

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
- **TeacherAssignment** (`id`, institution_id, campus_id, session_id, term_id?, class_level_id, arm_id, subject_id, employee_id/teacher, role [lead/assistant/substitute], workload/periods, effective_start/end, status, authorized_by)
- Relationships: Session 1—N Term; ClassLevel 1—N Arm; SubjectOffering links Subject to Class/Arm/period; TeacherAssignment links Employee to Subject/Class/Arm (historical, auditable); draft/versioned timetable slots enforce add-time teacher/class/room conflict checks. Recurrence, publication policy, and configurable workload are still open.

### 2.6 Attendance (M3 student slice implemented)
- **AttendanceSession** (`id`, institution_id, campus_id, subject_offering, date, status, opened_by/closed_by/timestamps) — staff/period-level sessions not implemented
- **AttendanceRecord** (`attendance_session_id`, student, status [present/absent/late/excused], marked_by, marked_at)
- **AttendanceCorrection** (`attendance_record_id`, previous_status, new_status, reason, corrected_by, corrected_at)
- Relationships: auditable corrections; summaries/exports and staff attendance remain planned.

### 2.7 Examinations, Results, Report Cards
- **AssessmentScheme** (`id`, institution_id, level/scope, session/term, effective dates, grading config ref) — preserved historically
- **AssessmentComponent** (`scheme_id`, type [CA/test/exam/etc], name, max_marks, weight, applicable scope)
- **GradingScale** (`id`, institution_id, name, effective dates, boundaries/grade/description/remarks/gpa rules as configured)
- **ResultRecord** (`id`, student_id, subject_offering_id, session_id, term_id, component scores, total, grade, computed fields metadata, status [draft/submitted/returned/resubmitted/approved/published])
- **ResultWorkflowAction** (`result_record_id` or batch, action, actor_id, timestamp, comments)
- **ResultCorrection** (`result_record_id`, original_values, revised_values, reason, requester, reviewer, approver, timestamps, prior_version_ref)
- **ReportCard** (`id`, student_id, session_id, term_id, generated_from published results snapshot/ref, template/version, status, file_ref, generated_at)
- Relationships: ResultRecord unique per student/subject/assessment/period (unless attempts configured); only approved/published feed report cards; corrections versioned, never silent overwrite.

### 2.8 Transcripts & Alumni
- **TranscriptRequest** (`id`, student_id, requested_by, purpose, status)
- **Transcript** (`id`, student_id, reference_number [unique], type/status [provisional/official], version, issued_by/approved_by, issued_at, file_ref, verification_token/hash, grading-scheme refs preserved)
- **TranscriptVerification** (lookup by token/ref exposing limited non-sensitive fields)
- **AlumniProfile** (`id`, student_id [unique link], alumni_number?, graduation_session/class, contact/career/engagement fields, privacy settings)
- Relationships: Student 1—0..1 AlumniProfile (linked, no duplicate person); transcripts trace to approved historical ResultRecords.

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

## 4. Implemented migration evidence (through M3)
- M1: `accounts`, `institutions`, `permissions`, `audit`.
- M2: `admissions`, `guardians`, `students`, `documents`, `imports`, identifier sequences/lifecycle history.
- M3: `employees/0001_initial.py`, `academics/0001_initial.py`, `teaching/0001_initial.py`, `attendance/0001_initial.py`, and permission seed `permissions/0004_seed_phase3_permissions.py`.
- Migration state validated with `manage.py makemigrations --check --dry-run` and `manage.py migrate`; M3 remains open for schema refinements from configurable workload, recurrence/publication, and staff attendance.

*This ER model is a living blueprint refined with migrations; final schema/MRD continues to be validated during implementation.*
