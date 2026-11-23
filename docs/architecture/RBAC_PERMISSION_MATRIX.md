# RBAC Permission Matrix

**Status:** Approved (2026-11-20) as the MVP authorization baseline; implemented and validated through M3, with M3 treated as an open hardening slice. Deny-by-default. Configurable per-verb grants are enforced by `HasModuleVerbPermission` for institution/campus context and M1–M3 modules; record-level predicates, approval thresholds, role-name alignment, and negative API tests remain outstanding.

## 1. Principles
- **Deny-by-default:** no access unless explicitly granted.
- **Scope-aware:** permissions evaluated against institution, campus, assigned class/arm, assigned subject, assigned record, or own profile.
- **Backend authoritative:** frontend hides/disables by role, but APIs/services/jobs enforce authorization.
- **Separation of duties (configurable):** e.g. result entry vs approval; requester vs approver for sensitive finance/procurement/actions where policy requires.
- **Audit:** sensitive actions logged (who, what, target, when, reason/change summary).

## 2. Actions (standard verbs)
`view, create, update, delete_or_archive, submit, review, approve, publish, export, print, reverse_or_refund, issue_or_revoke`

## 3. Roles (suggested, configurable)
Super Administrator, Institution Administrator, Campus Administrator, Principal/Head Teacher, Vice Principal/Deputy Head, Head of Department, Class Teacher, Subject Teacher, Assistant Teacher, Examination Officer, Registrar/Admissions Officer, Bursar/Accountant, HR Officer, Librarian, Transport Officer, Parent/Guardian, Student, Alumni, Website Editor. (Users may hold multiple roles; effective permissions are scoped.)

## 4. Permission Matrix (MVP-focused, high level)

Legend: **F**=Full (within scope), **S**=Scoped/limited, **O**=Own/linked only, **A**=Approval/review capable, **R**=Read-only, **-**=No access. Exact CRUD per verb to be detailed in implementation.

| Module / Resource | Super/Inst Admin | Campus Admin | Principal/VP | HoD | Class Teacher | Subject Teacher | Exam Officer | Registrar/Admissions | Bursar/Accountant | HR Officer | Website Editor | Parent/Guardian | Student | Alumni |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Institution/Campus/Settings | F | S(campus) | R/S | R | - | - | - | R | R | R | R | - | - | - |
| Users/Roles/Permissions | F | S | - | - | - | - | - | - | - | S(HR scope) | - | - | - | - |
| Students (profiles/lifecycle) | F | S | S | S | S(class) | S(assigned students, view limited) | S | F(admissions/enrol) | R(finance link) | R | - | O(linked) | O(self) | O(linked self via alumni profile) |
| Guardians & relationships | F | S | S | - | S(class) | R(limited) | - | F | R | - | - | O(self/linked) | - | - |
| Admissions/Enquiries/Applications | F | S | S/A | - | - | - | - | F (create/review/process) | R(fees) | - | - | S(applicant/own where enabled) | - | - |
| Academic structure (sessions/terms/classes/arms/subjects/offerings) — M3 | F | S | S/A | S(dept) | R(class) | R(assigned) | S | R | - | - | - | R(limited) | R(limited) | - |
| Teacher allocations (teaching) — M3 | F | S | S/A | S/A(dept) | R(own class context) | R(own) | R | R | - | R(staff refs) | - | - | - | - |
| Timetable (draft/versioned slots) — M3 | F | S | S/A | S | R(class) | R(own) | R | R | - | - | - | R(linked) | R(self) | - |
| Attendance (student offering-based; staff not implemented) — M3 | F | S | S | S | S(class mark/correct*) | S(assigned class/subject mark*) | R | R | - | S(staff) | - | R(linked) | R(self) | - |
| Assessments/Results (entry/workflow) | F | S | A | A(review scope) | R(class overview) | S(entry/submit for assigned only) | F/A(config/workflow) | R | - | - | - | R(published, linked) | R(published, self) | - |
| Report cards | F | S | A/publish | R | R(class) | R(assigned) | S(generate/manage per policy) | R | - | - | - | R(published, linked) | R(published, self) | - |
| Transcripts (official) | F | S | A/issue | R | - | - | S/A(per policy) | S(request/admin) | - | - | - | R/Request*(policy) | R/Request*(policy) | R/Request*(policy) |
| Finance (fees/invoices/payments/receipts) | F | S | R/A(policy) | - | - | - | - | R | F (post/reconcile; reverse/refund with A) | - | - | R/O(linked) pay/view* | R/O(self)* | - |
| Inventory/Procurement/Assets (MVP basic assets) | F | S | A | S(dept) | R/request* | R/request* | - | - | S(cost/approve per policy) | - | - | - | - | - |
| ID Cards | F | S | A | - | R | R | - | S(generate per policy) | - | S(staff cards) | - | R(own status*) | R(own status*) | - |
| CMS / Public website | F | S | A(publish) | - | - | - | - | - | - | - | F(content; publish per policy) | - | - | - |
| Communications/Notifications | F | S | S | S | S(class) | S(assigned) | S | S | S(finance notices) | S | S(public notices) | R(receive) | R(receive) | R(receive) |
| Reports/Dashboards/Exports | F | S | S | S | S(class) | S(assigned) | S | S | S(finance) | S | S(web) | R(limited linked) | R(limited self) | R(limited self) |
| Audit logs | F (view) | R(scoped) | R(scoped) | - | - | - | R(scoped) | R(scoped) | R(scoped) | - | - | - | - | - |

`*` = subject to specific policy/workflow constraints (e.g. corrections require reason/approval, payments require verification, transcript requests/issuance controlled).

## 5. Scoped Permission Rules (must enforce)
- **Institution/Campus:** no cross-institution access; campus-scoped roles limited to assigned campus records.
- **Subject Teacher:** may `create/update/submit` results/attendance **only** for assigned subject/class/arm/session/term; no authority over unassigned scopes unless separately authorized.
- **Class Teacher:** overall class view for assigned class/arm; **not** automatic edit rights for all subjects' marks.
- **Parent/Guardian:** access only students explicitly linked and authorized; restricted fields per policy.
- **Student/Alumni:** own/linked records only; alumni access separate from active-student access.
- **Finance/Procurement:** segregation-of-duties configurable (requester vs approver; no self-approval where enabled); reverse/refund/adjustment require authorization.
- **CMS:** publication workflow permissions; public endpoints expose only explicitly published public fields.

## 6. Sensitive Actions & Approval (examples)
- Publish/approve results; correct approved results; issue/correct/revoke transcripts and ID cards.
- Post/verify/reverse/refund financial transactions.
- Approve high-value PO/GRN discrepancies/stock adjustments/asset disposal (per thresholds).
- Grant/modify roles/permissions; cross-scope overrides.
All require audit records; some require second approver per institution policy (to be configured).

## 7. Details to refine during implementation (non-blocking)
- Exact per-verb grants per role, record-level predicates, and approval thresholds.
- HoD/Exam Officer granular review powers per school policy.
- Parent/student request rights for transcripts/certificates and payable actions.
- **M3:** `academics`, `teaching`, `attendance`, and `employees` module grants are seeded in data; role names must be normalized to the matrix (`Principal/VP`/`HoD` vs current `Academic Head`/`Teacher`) before M3 acceptance.
*Encode as configurable RBAC data and validate with negative authorization tests in each phase. Refinement does not block progression to Phase 2, but the M3 items above block M3 acceptance.*

## 8. Implemented M3 enforcement notes
- `employees`: `view/create/update` for admins/Registrar/Academic Head; `delete_or_archive`/`export` admin-only.
- `academics`: `view` for admins/Registrar/Academic Head/Teacher; `create/update` for admins/Registrar/Academic Head; `publish` for admins/Academic Head; `delete/export` admin-only.
- `teaching`: `view` for admins/Registrar/Academic Head/Teacher; assignment mutations and `approve/publish` for admins/Academic Head.
- `attendance`: `view/create` for admins/Registrar/Academic Head/Teacher; correction/`update`/`approve` for admins/Academic Head; `export` admin-only; `print` for admins/Registrar/Academic Head/Teacher.
- Assignment/attendance service methods enforce assigned-class/subject scope, but cross-scope queryset filtering, API role/negative tests, and staff attendance remain open.
