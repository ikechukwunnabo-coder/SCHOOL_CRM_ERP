# RBAC Permission Matrix

**Status:** Draft (documented, not implemented). Deny-by-default. Final matrix to be reviewed/approved and encoded as configurable data.

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
| Academic structure (sessions/terms/classes/arms/subjects) | F | S | S/A | S(dept) | R(class) | R(assigned) | S | R | - | - | - | R(limited) | R(limited) | - |
| Teacher allocations (teaching) | F | S | S/A | S/A(dept) | R(own class context) | R(own) | R | R | - | R(staff refs) | - | - | - | - |
| Timetable | F | S | S/A | S | R(class) | R(own) | R | R | - | - | - | R(linked) | R(self) | - |
| Attendance (student/staff) | F | S | S | S | S(class mark/correct*) | S(assigned class/subject mark*) | R | R | - | S(staff) | - | R(linked) | R(self) | - |
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

## 7. Gaps to finalize (Pending)
- Exact per-verb grants per role, record-level predicates, and approval thresholds.
- HoD/Exam Officer granular review powers per school policy.
- Parent/student request rights for transcripts/certificates and payable actions.
*To be encoded as configurable RBAC data and validated with negative authorization tests.*
