# Data Dictionary

**Status:** Living dictionary. M1/M2 fields and the M3 academic/teaching/attendance slice are implemented in migrations; values below are representative, not exhaustive. Phase 4+ entities remain blueprint-only.

## 1. Conventions
- **Types:** `uuid`, `string(n)`, `text`, `int`, `decimal(p,s)`, `bool`, `date`, `datetime(tz)`, `jsonb`, `enum`.
- **Common fields:** `id (uuid, PK)`, `institution_id (uuid, FK, not null)` for owned records, `campus_id (uuid, FK, nullable/required by entity)`, `created_at/updated_at (datetime tz)`, `created_by/updated_by (uuid FK user, nullable where system)`, `status/is_active` as applicable.
- **Validation:** required vs optional per workflow; DB constraints (unique, FK, check, not null) and app-level validation must align.

## 2. Core Entities (selected)

### Institution / Campus
| Entity | Field | Type | Req | Notes/Validation |
|---|---|---|---|---|
| Institution | name | string | Y | legal/display name |
|  | code | string | Y | unique code/slug |
|  | settings | jsonb | N | locale, timezone, currency, date format, policies |
| Campus | institution_id | uuid FK | Y | scoped to institution |
|  | name, code | string | Y | unique within institution (recommended) |

### User / RBAC
| Entity | Field | Type | Req | Notes/Validation |
|---|---|---|---|---|
| User | institution_id | uuid FK | Y | tenant scope |
|  | email | string | Y | unique (scoped as defined), valid format |
|  | password_hash | string | Y | Django-supported hasher; never plaintext |
|  | is_active | bool | Y | auth gate |
| Role | name | string | Y | configurable; unique per institution/template |
| UserRole | user_id, role_id | uuid FK | Y | scoped assignment |
|  | scope_type | enum | Y | institution/campus/class/subject/record/own |
|  | scope_ref_id | uuid | N | target of scope |
| AuditLog | actor_user_id | uuid FK | N | system actions nullable with marker |
|  | action, target_type, target_id | string/uuid | Y | immutable record |
|  | change_summary | jsonb/text | N | safe, non-sensitive summary |

### Student / Guardian / Admissions
| Entity | Field | Type | Req | Notes/Validation |
|---|---|---|---|---|
| Student | admission_number | string | Y | **unique per defined scope**, immutable once issued (controlled correction only) |
|  | lifecycle_state | enum | Y | Applicant→…→Graduated/Withdrawn/etc; transitions validated/audited |
|  | dob, gender, photo_ref | date/enum/ref | per policy | restricted/optional by policy |
|  | current_campus_id | uuid FK | Y | |
| StudentGuardian | student_id, guardian_id | uuid FK | Y | unique pair constraint |
|  | relationship | string/enum | Y | |
|  | portal_access | bool | Y | drives authorized access |
| Application | application_number | string | Y | unique scoped |
|  | status | enum | Y | Enquiry→Submitted→…→Enrolled/Rejected/etc |
|  | intended_class_id, intended_campus_id | uuid FK | Y | |

### Academics / Teaching (M3 implemented slice)
| Entity | Field | Type | Req | Notes/Validation |
|---|---|---|---|---|
| AcademicSession | institution_id, code, name, start_date, end_date | uuid FK/string/date | Y | code unique per institution; end_date >= start_date; campus optional |
|  | is_closed | bool | Y | current/closure marker; non-overlap policy not yet enforced |
| Term | session_id, code, name, start_date, end_date | uuid FK/string/date | Y | code unique per session; end_date >= start_date |
| ClassLevel | institution_id, code, name, sequence | uuid FK/string/int | Y | code unique per institution |
| Arm | class_level_id, code, name | uuid FK/string | Y | code unique per class level |
| Subject | institution_id, code, name | uuid FK/string | Y | code unique per institution |
| SubjectOffering | session_id, term_id, class_level_id, arm_id, subject_id | uuid FK | Y/N | unique scope; term/arm optional |
|  | is_compulsory | bool | Y | offering flag |
| ClassEnrolment | session_id, student_id, class_level_id, arm_id, status | uuid FK/enum | Y/N | unique session+student; status active/completed/withdrawn |
| TeacherAssignment | institution_id, campus_id, session_id, term_id, class_level_id, arm_id, offering_id, employee_id | uuid FK | Y/N | effective-dated allocation |
|  | role, status | enum | Y | lead/assistant/substitute; active/closed |
|  | start_date, end_date | date | Y | history preserved on reassignment |
|  | workload_hours | int | Y | default 0; service currently enforces a hard-coded 40-hour cap (make configurable) |
| Timetable | session_id, class_level_id, arm_id, name, version, status | uuid FK/string/int/enum | Y | draft/published; version unique per scope |
| TimetableSlot | timetable_id, day_of_week, period, offering_id, employee_id, room | uuid FK/int/string | Y | add-time conflict checks; one slot per day/period per timetable |

### Attendance (M3 implemented student slice)
| Entity | Field | Type | Req | Notes/Validation |
|---|---|---|---|---|
| AttendanceSession | institution_id, campus_id, session_id, term_id, class_level_id, arm_id, offering_id, attendance_date | uuid FK/date | Y/N | unique offering+date; student/subject-offering based |
|  | status, closed_by | enum/uuid FK | Y/N | open/closed; staff/period sessions not implemented |
| AttendanceRecord | attendance_session_id, student_id, status, marked_by, marked_at, correction_count | uuid FK/enum/datetime/int | Y | unique session+student; present/absent/late/excused |
| AttendanceCorrection | record_id, previous_status, new_status, reason, requested_by, approved_by | uuid FK/enum/text/uuid FK | Y | mandatory reason; privileged approval; application-level audit |

### Examinations / Results / Transcripts
| Entity | Field | Type | Req | Notes/Validation |
|---|---|---|---|---|
| AssessmentComponent | max_marks | decimal | Y | > 0 |
|  | weight | decimal | Y | scheme weights sum/validation per config |
| GradingScale | effective_from/to | date | Y/N | preserved historically; not retro-applied |
| ResultRecord | student_id, subject_offering_id, session_id, term_id | uuid FK | Y | **unique combo** (unless attempts configured) |
|  | total_score, grade | decimal/string | N/Y | computed by controlled service |
|  | status | enum | Y | draft→submitted→returned→resubmitted→approved→published |
| ResultCorrection | original_values,revised_values | jsonb | Y | reason, requester/reviewer/approver, timestamps |
| Transcript | reference_number | string | Y | **unique**, immutable once issued |
|  | verification_token | string/hash | Y | non-guessable; no sensitive data encoded in QR |
|  | version, status | int/enum | Y | provisional/official; reissue preserves history |

### Finance
| Entity | Field | Type | Req | Notes/Validation |
|---|---|---|---|---|
| FeeSchedule | currency | string(3) | Y | default NGN; stored on txns/invoices |
|  | amount | decimal(p,s) | Y | >= 0 |
| Invoice | invoice_number | string | Y | unique scoped |
|  | status | enum | Y | draft/issued/part-paid/paid/voided (void via controlled flow) |
| Payment | receipt_number | string | Y | unique scoped |
|  | provider_ref | string | N | gateway ref; idempotency key tracked |
|  | status | enum | Y | pending/verified/failed/reversed/refunded |
| FinancialAdjustment | type | enum | Y | refund/reversal/credit/waiver; authorized & audited; posted txns not deleted |

### Inventory / Procurement / Assets
| Entity | Field | Type | Req | Notes/Validation |
|---|---|---|---|---|
| Item | sku_code | string | Y | unique scoped |
|  | type | enum | Y | consumable/stock/non-stock/asset-controlled |
| StockMovement | qty | decimal/int | Y | signed/typed; transactional; no unapproved negative stock |
|  | ref_type/ref_id | string/uuid | Y | traceability (GRN/issue/transfer/etc.) |
| PurchaseOrder | po_number | string | Y | unique scoped |
| Asset | asset_number | string | Y | unique tag/number |
|  | condition,status | enum | Y | lifecycle tracked |
|  | custodian_employee_id | uuid FK | N | current custodian; history in AssetHistory |

### Identity Cards / CMS / Communications
| Entity | Field | Type | Req | Notes/Validation |
|---|---|---|---|---|
| IdCard | verification_token | string | Y | random non-guessable; QR target |
|  | status | enum | Y | draft→generated→approved→issued→active→expired/revoked/replaced |
| CmsPage | slug | string | Y | unique per site/institution; published flag controls public visibility |
|  | status | enum | Y | draft/review/published/archived |
| NotificationLog | channel | enum | Y | in-app/email/sms/(whatsapp later) |
|  | delivery_status | enum | Y | queued/sent/failed; retries logged |

## 3. Data Quality & Integrity Rules
- Enforce uniqueness, FK integrity, and checks at DB level; mirror in application validation.
- Use transactions for multi-step state changes (enrolment, result publish, payments/allocations, stock moves).
- Preserve history: lifecycle events, allocations, attendance corrections, result corrections/versions, transcript issues, asset custody, financial adjustments.
- Separate public CMS fields/media from confidential ERP records and private documents.

*Expand this dictionary per entity/table as migrations evolve; M3 refinements needed for configurable workload, timetable recurrence/publication, and staff attendance.*
