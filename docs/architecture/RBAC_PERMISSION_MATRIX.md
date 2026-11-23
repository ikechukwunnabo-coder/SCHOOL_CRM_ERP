# RBAC Permission Matrix

**Status:** Approved (2026-11-20) as the MVP authorization baseline; implemented locally through M3/M4 hardening. Deny-by-default. Configurable per-verb grants are enforced by `HasModuleVerbPermission` for institution/campus context and M1–M4 modules, with object-level queryset scoping, canonical role names plus backward-compatible aliases, and role/negative plus cross-scope/IDOR API tests. M3/M4 remain not accepted pending UAT/sign-off and Q-003; approval thresholds and remaining domain-specific predicates continue to be refined.

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
| Timetable (recurrence + draft/approve/publish/revise) — M3 | F | S | S/A | S | R(class) | R(own) | R | R | - | - | - | R(linked) | R(self) | - |
| Attendance (student offering-based + teacher attendance) — M3 | F | S | S | S | S(class mark/correct*) | S(assigned class/subject mark*) | R | R | - | S(staff) | - | R(linked) | R(self) | - |
| Assessments/Results (entry/workflow) — M4 backend | F | S | A | A(review scope) | R(class overview) | S(entry/submit for assigned only) | F/A(config/workflow) | R | - | - | - | R(published, linked; portal pending) | R(published, self; portal pending) | - |
| Report cards — M4 | F | S | A/publish | R | R(class) | R(assigned) | S(generate/manage per policy) | R | - | - | - | R(published, linked; portal pending) | R(published, self; portal pending) | - |
| Transcripts (official) | F | S | A/issue | R | - | - | S/A(per policy) | S(request/admin) | - | - | - | R/Request*(policy) | R/Request*(policy) | R/Request*(policy) |
| Alumni records (graduation-linked) — M4 closure | F | S | R | R | R(linked) | R(linked) | R | R | - | - | - | R(linked) | R(self, after linkage) | O(self) |
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
- **M3/M4:** `academics`, `teaching`, `attendance`, `employees`, `examinations`, `transcripts`, and `alumni` module grants are seeded in data. Canonical role names match the matrix, with backward-compatible aliases (`Academic Head` → `Head of Department`, `Teacher` → `Subject Teacher`, `Principal` → `Principal/Head Teacher`, `Principal/VP` → `Principal/Head Teacher` + `Vice Principal/Deputy Head`).
*Encode as configurable RBAC data and validate with negative authorization tests in each phase. M3/M4 role-name alignment and negative/cross-scope tests are closed locally; formal UAT/sign-off and Q-003 remain before acceptance.*

## 8. Implemented M3 enforcement notes
- `employees`: `view/create/update` for admins/Registrar/Academic Head; `delete_or_archive`/`export` admin-only.
- `academics`: `view` for admins/Registrar/Academic Head/Teacher; `create/update` for admins/Registrar/Academic Head; `publish` for admins/Academic Head; `delete/export` admin-only.
- `teaching`: `view` for admins/Registrar/Academic Head/Teacher; assignment mutations and `approve/publish` for admins/Academic Head.
- `attendance`: `view/create` for admins/Registrar/Academic Head/Teacher; correction/`update`/`approve` for admins/Academic Head; `export` admin-only; `print` for admins/Registrar/Academic Head/Teacher.
- Object-level institution/campus/record queryset scoping is implemented for M3 APIs; teacher scope is enforced in services and querysets.
- Role/negative and cross-scope/IDOR API tests cover M3 grants; workload policy, timetable recurrence/publish, and teacher attendance are implemented locally.

## 9. Implemented M4 backend enforcement notes
- `examinations`: `view` for admins/Registrar/Academic Head/Teacher/Examination Officer/Principal-VP; `create/update/submit` for admins/Academic Head/Teacher/Examination Officer.
- `examinations`: `review` for admins/Academic Head/Examination Officer/Principal-VP; `approve/publish` for admins/Examination Officer/Principal-VP; `delete_or_archive` admin-only.
- Result services enforce assigned-offering scope for teachers and deny self-approval; corrections require reason and return the record to submitted status for re-approval.
- API role/negative tests cover teacher denial and Examination Officer approval/publication; parent/student portal views remain unimplemented.
- `transcripts`: `view/download/print` for admins/Registrar/Academic Head/Examination Officer/Principal-VP; `create` for admins/Registrar/Examination Officer; `update`/correction for admins/Registrar; `review` for admins/Academic Head/Examination Officer/Principal-VP; `approve` for admins/Examination Officer/Principal-VP; `issue_or_revoke` for admins/Registrar/Principal-VP; `delete_or_archive` admin-only.
- Transcript services enforce institution/campus scope, deny request self-approval, require reasons for rejection/correction/revocation, and preserve prior versions/snapshots; public verification is hash-token-only and returns no student personal data.
- Transcript API role/negative tests cover teacher denial and registrar request/generate/issue/download plus public verification; parent/student portal views remain unimplemented.
- M4 closure adds object-level queryset scoping and cross-scope/IDOR tests, effective-dated grading policy, private PDF report-card download, and read-only graduation-linked alumni records via `/api/v1/alumni/records/`. These are validated locally, not accepted; Q-003 and UAT/sign-off remain.
