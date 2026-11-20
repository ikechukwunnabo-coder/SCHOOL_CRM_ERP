# SCHOOL CRM & ERP PLATFORM
## Authoritative Master Prompt, Technical Specification and Implementation Brief

**Document:** `CRM_ERP_SCHOOL_PROMPT.md`  
**Purpose:** Build a secure, scalable, maintainable School CRM and ERP platform with an integrated public website and CMS.  
**Instruction to the AI development agent:** Treat this document as the authoritative baseline specification. Do not silently omit requirements, invent business rules, or claim functionality is complete without implementation and test evidence.

---

# 1. Project Overview

Design and develop a comprehensive School Customer Relationship Management (CRM) and Enterprise Resource Planning (ERP) platform for managing the complete operational, academic, administrative, financial and communication activities of an educational institution.

The platform must provide a unified system for:

- School management and administration.
- Student recruitment, enquiries, admissions and enrolment.
- Student records and lifecycle management.
- Parent and guardian relationship management.
- Academic sessions, terms, classes, arms, subjects and curriculum.
- Subject teacher allocation and teacher workload management.
- Timetables, attendance and academic activities.
- Continuous assessment, examinations, results and report cards.
- Cumulative student transcripts and transcript verification.
- Fees, invoices, payments and financial reporting.
- Staff and teacher records.
- Parent, student, teacher and administrative portals.
- Alumni records and alumni engagement.
- Public school website managed through an integrated CMS.
- Dashboards, reports, notifications, audit trails and system configuration.

The application must be designed for real institutional use, not as a demonstration or a collection of disconnected CRUD screens. All modules must share consistent data, permissions, workflows and audit controls.

# 2. Decisions, Assumptions and Scope

Use the following as the initial baseline. Make these settings configurable rather than hardcoding them throughout the application.

| Area | Initial baseline |
|---|---|
| Institution type | Nursery, Primary and Secondary School |
| Initial country | Nigeria |
| Initial deployment | One institution, with support for multiple campuses |
| Future readiness | Architect the data model for multiple institutions without prematurely building a public SaaS service |
| Public website | Integrated with the ERP and managed through its CMS |
| Architecture | Modular monolith |
| Backend | Python, Django and Django REST Framework |
| Frontend | React with TypeScript |
| Database | PostgreSQL |
| Default currency | Nigerian Naira (NGN) |
| Default locale | English (Nigeria), `en-NG` |
| Default timezone | `Africa/Lagos`, configurable |
| Date display | `DD/MM/YYYY`, configurable |
| Alumni | Retain Alumni Management as a defined module |
| Transcript | Official cumulative transcript generated from approved historical academic records |
| Deployment | Docker-based deployment with separate development, staging and production environments |

Before implementation, produce a **Decisions and Open Questions Register**. Record any requirement that cannot safely be inferred. Ask the project owner only questions that materially affect architecture or business rules. Do not block all progress on cosmetic preferences; use documented, reversible defaults where appropriate.

# 3. Release Scope and Priorities

Do not attempt to implement every possible school module at once. Deliver a stable MVP first, then extend it in controlled releases.

## Release 1 — Core MVP

The first production-capable release must include:

1. Authentication, user management and role-based access control.
2. Institution, campus and school configuration.
3. Student CRM, enquiries, admissions and enrolment.
4. Parent and guardian records and relationships.
5. Teacher and employee basic records.
6. Academic sessions, terms, classes, arms and subjects.
7. Subject teacher allocation and teaching assignments.
8. Timetable management.
9. Student and teacher attendance.
10. Continuous assessment and examination setup.
11. Result entry, submission, review, approval and publication.
12. Student report cards and cumulative transcripts.
13. Basic fee structures, invoices, payments and balances.
14. Parent and teacher portals.
15. Integrated public website and CMS.
16. Core dashboards, reports, notifications and audit logs.
17. Student lifecycle management, including graduation and creation/linkage of an alumni record.
18. Basic asset register for recording school-owned assets, including unique asset IDs, category, location, custodian, condition and status.

## Release 2 — Extended School Operations

Plan these as separate modules with clean integration points:

- Full accounting and double-entry general ledger.
- HR management, leave and payroll.
- Full inventory, stores, procurement and asset management, building on the basic MVP asset register.
- Library management.
- Transport and school bus management.
- Hostel/boarding management, if applicable.
- Learning Management System (LMS).
- Full alumni portal, directory, events and engagement.
- Advanced analytics and management reporting.

## Release 3 — Optional Advanced Capabilities

Do not implement these before the core platform is stable:

- WhatsApp Business integration.
- Biometric attendance.
- GPS-enabled school transport tracking.
- Online examinations.
- Advanced AI-assisted analytics and administrative assistance.
- Multi-institution SaaS subscription and billing.
- Additional third-party integrations.

# 4. Technology Stack and Engineering Standards

Use a modern, production-oriented stack. At project initiation, verify official compatibility and security support for all selected versions. Pin exact compatible versions in dependency files and commit lockfiles. Do not blindly install unpinned latest versions.

## Backend

- Python 3.14 or a compatible supported version.
- Django 5.2 LTS.
- Django REST Framework.
- PostgreSQL, using a supported version compatible with the deployment environment.
- Redis for caching and background-job infrastructure.
- Celery for asynchronous and scheduled tasks.
- OpenAPI schema and browsable API documentation.
- Gunicorn for production application serving.
- Nginx as reverse proxy and static/media delivery layer where appropriate.

## Frontend

- React.
- TypeScript with strict type checking.
- Vite.
- Tailwind CSS.
- shadcn/ui or a consistent accessible component system.
- TanStack Query for server state.
- React Hook Form and Zod for form handling and validation.
- Recharts or an equivalent maintained charting library.
- A consistent routing solution.
- Responsive, accessible layouts.

## Infrastructure and delivery

- Docker and Docker Compose for reproducible local development.
- Separate development, staging and production configurations.
- Environment-based configuration and secret management.
- CI pipeline for formatting, linting, type checking, tests and build verification.
- Database migration strategy.
- Structured application logs and error monitoring.
- Automated backup and restore procedures.
- Production deployment documentation.

## Project directory

Use a clear project root, for example:

```text
school_erp/
├── backend/
├── frontend/
├── infrastructure/
├── docs/
├── scripts/
├── tests/
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

Create the Python virtual environment as `school_erp_venv/` at the project root if the development environment requires a local virtual environment. Do not commit the virtual environment to source control.

# 5. Architecture and Module Boundaries

Use a **modular monolith** for the initial implementation. Modules must have clear ownership and communicate through documented service interfaces, domain events or APIs. Avoid unnecessary microservices.

Suggested backend app boundaries:

```text
backend/
├── config/
├── apps/
│   ├── core/
│   ├── institutions/
│   ├── accounts/
│   ├── permissions/
│   ├── students/
│   ├── admissions/
│   ├── guardians/
│   ├── employees/
│   ├── academics/
│   ├── teaching/
│   ├── attendance/
│   ├── examinations/
│   ├── transcripts/
│   ├── finance/
│   ├── inventory/
│   ├── procurement/
│   ├── asset_management/
│   ├── communications/
│   ├── portals/
│   ├── cms/
│   ├── alumni/
│   ├── reporting/
│   ├── audit/
│   └── integrations/
└── manage.py
```

The exact app names may be refined during architecture design, but ownership must remain clear:

- `institutions`: schools, campuses, institution settings and tenant context.
- `students`: student identity, admission number, enrolment and lifecycle.
- `admissions`: enquiries, applications, admission decisions and onboarding.
- `guardians`: parent/guardian profiles and student relationships.
- `employees`: staff identity and employment records.
- `academics`: academic years/sessions, terms, classes, arms, subjects, curriculum and academic structure.
- `teaching`: teacher-to-subject/class assignments, teaching roles and workload.
- `attendance`: attendance sessions, marks, corrections and summaries.
- `examinations`: assessment structures, marks, result calculations and approval workflow.
- `transcripts`: official transcript generation, issuance, versioning and verification.
- `finance`: fee schedules, invoices, payments, allocations, refunds and balances.
- `inventory`: stock items, categories, stores/locations, stock balances, receipts, issues, transfers, adjustments and stock counts.
- `procurement`: purchase requests, approvals, supplier quotations, purchase orders, goods received and supplier records.
- `asset_management`: capital/non-consumable assets, asset register, tagging, assignment, custody, movement, maintenance, depreciation configuration where required, verification and disposal.
- `cms`: public website pages, menus, media and publishing workflow.
- `alumni`: alumni profiles and engagement linked to the original student record.
- `audit`: immutable or tamper-evident records of sensitive actions.

Do not duplicate the same business entity in multiple apps. Document cross-module dependencies and avoid circular imports.

# 6. Institution, Campus and Data Isolation

The initial installation may serve one institution with multiple campuses. Nevertheless, the data model should include an institution/school context from the beginning.

Requirements:

- Every institution-owned record must be associated with the correct institution.
- Campus-specific records must also carry a campus reference where relevant.
- Enforce institution and campus scope in API querysets, service methods and background jobs.
- Never rely only on frontend filtering for data isolation.
- Use institution-scoped unique constraints where appropriate.
- Prevent users from accessing records belonging to another institution or an unauthorized campus.
- Include automated tests for cross-institution and cross-campus access attempts.
- Document the future multi-tenant strategy before enabling multiple customer institutions in a shared production environment.

# 7. Authentication, Accounts and Access Control

Implement secure authentication and authorization.

## Authentication

Choose and document one primary authentication approach. For a same-site React and Django deployment, prefer secure, HttpOnly cookie-based authentication with appropriate CSRF protection.

Requirements include:

- Secure password hashing using Django's supported password hashers.
- Secure, HttpOnly and appropriately SameSite-configured cookies.
- CSRF protection for cookie-authenticated state-changing requests.
- Short-lived access credentials and rotating refresh credentials if using token-based authentication.
- Refresh-token revocation/blacklisting and logout invalidation.
- Login throttling and protection against brute-force attempts.
- Password reset using time-limited, single-use tokens.
- Optional multi-factor authentication as a later enhancement or configurable security feature.
- Session/device management where feasible.
- Never store long-lived authentication tokens in browser local storage.
- Never expose secrets in frontend bundles, logs or source control.

## Role-based access control

Implement granular RBAC with deny-by-default behaviour.

Suggested roles:

- Super Administrator.
- Institution Administrator.
- Campus Administrator.
- Principal/Head Teacher.
- Vice Principal/Deputy Head.
- Head of Department.
- Class Teacher.
- Subject Teacher.
- Assistant Teacher.
- Examination Officer.
- Registrar/Admissions Officer.
- Bursar/Accountant.
- HR Officer.
- Librarian.
- Transport Officer.
- Parent/Guardian.
- Student.
- Alumni.
- Website Editor.

Roles must be configurable. A user may have multiple roles, but permissions must be evaluated against the current institution, campus, class, subject and record context.

Permissions must distinguish:

- View.
- Create.
- Update.
- Delete or archive.
- Submit.
- Review.
- Approve.
- Publish.
- Export.
- Print.
- Reverse or refund.
- Issue or revoke official documents.

Support scoped permissions, including:

- Institution-wide.
- Campus-specific.
- Assigned class/arm.
- Assigned subject.
- Assigned student or record.
- Own profile only.

Sensitive actions must be logged. Where configured, require a second authorized approver for result publication, transcript issuance/correction, financial reversal/refund and permission escalation.

# 8. Student CRM and Admissions

Create a complete student relationship and admissions workflow.

## Enquiries and prospective students

Capture:

- Applicant/student name.
- Date of birth.
- Gender, where required by the institution.
- Contact information.
- Parent/guardian information.
- Intended class and campus.
- Source of enquiry.
- Enquiry date and follow-up status.
- Notes and communication history.

## Application and admission workflow

Support configurable statuses such as:

`Enquiry → Application Started → Submitted → Under Review → Assessment/Interview → Approved → Offered → Accepted → Enrolled`

Also support rejected, withdrawn, waitlisted and deferred outcomes.

Requirements:

- Application forms configurable by institution and admission cycle.
- Required-document checklist.
- Document upload and review.
- Admission decision and approval records.
- Offer and acceptance tracking.
- Conversion of an accepted applicant into a student without duplicating identity data.
- Admission number generation using a configurable pattern.
- Admission audit trail.

# 9. Student Records and Lifecycle Management

Maintain a complete, longitudinal student record.

Capture, as appropriate:

- Student biodata and photograph.
- Admission number and internal unique ID.
- Date of admission.
- Current and historical campus.
- Current and historical class/arm.
- Parent/guardian relationships.
- Emergency contacts.
- Medical or welfare information with restricted access.
- Previous school information.
- Uploaded documents.
- Attendance history.
- Academic history.
- Fee and payment history.
- Disciplinary and pastoral records, with restricted access.
- Promotion, repetition, transfer, withdrawal and graduation history.

## Lifecycle state model

Support controlled transitions such as:

`Applicant → Admitted → Enrolled → Active → Promoted / Repeated / Transferred / Withdrawn / Graduated`

A graduated student may transition to an alumni status/profile.

Rules:

- Validate every lifecycle transition.
- Record who performed the transition, when and why.
- Do not delete academic history when a student changes class, campus or status.
- Re-admission must preserve the original identity and historical records while creating a new enrolment period where appropriate.
- Withdrawal must not erase financial or academic obligations.
- Graduation must preserve the complete academic record and enable alumni linkage.
- Avoid hard deletion of official student records except through a legally approved retention process.

# 10. Parent and Guardian Management

Support one or more parents/guardians per student and one guardian linked to multiple students.

Capture:

- Names and relationship.
- Contact numbers and email addresses.
- Address.
- Emergency contact status.
- Authorized pickup status, if used.
- Portal access status.
- Communication preferences.
- Financial responsibility relationship, where applicable.

Support controlled access so a parent sees only students for whom they are authorized.

# 11. Academic Structure and Calendar

Allow administrators to configure the institution's academic structure.

Core entities:

- Academic session/year.
- Term or semester.
- Campus.
- Class/grade/level.
- Arm/section/stream.
- Subject.
- Curriculum or subject offering.
- Enrolment.
- Timetable.
- Academic calendar events.

Requirements:

- Configurable academic year start and end.
- Configurable number and naming of terms/semesters.
- Configurable promotion rules.
- Historical academic structures must remain available.
- Closing a term/session must not rewrite previous records.
- Class and arm changes must be recorded historically.
- Support nursery, primary and secondary levels without assuming every school uses identical structures.

# 12. Subject and Teacher Management

This is a core requirement and must not be treated as an optional enhancement.

## Subject management

Administrators must be able to:

- Create and configure subjects.
- Assign subjects to class/grade and arm.
- Define compulsory and optional subjects.
- Configure subject codes and descriptions.
- Set subject status and effective academic session.
- Maintain historical subject offerings.

## Teacher allocation

Create a dedicated teacher-subject-class allocation model.

Each allocation should capture:

- Institution and campus.
- Academic session and term, where relevant.
- Class/grade.
- Arm/section.
- Subject.
- Assigned teacher.
- Teaching role.
- Effective start and end dates.
- Allocation status.
- Workload/period allocation, if used.
- Allocation history and authorizing administrator.

Support:

- One teacher teaching multiple subjects.
- One teacher teaching multiple classes and arms.
- Multiple teachers assigned to the same subject/class where the institution requires it.
- Primary/lead subject teacher.
- Assistant or supporting teacher.
- Substitute/temporary teacher assignment.
- Teacher reassignment during a session.
- Teacher workload and timetable conflict checks.

## Teacher authority

A subject teacher may enter marks only for the subjects, classes, arms and academic periods to which the teacher is assigned, subject to additional permissions.

A class teacher may view the overall performance of students in the assigned class but must not automatically gain permission to alter marks for every subject.

A Head of Department or Examination Officer may receive review permissions according to institution policy.

All teacher allocation changes and result-entry actions must be auditable.

# 13. Timetable Management

Provide timetable creation and management for:

- Classes and arms.
- Subjects.
- Teachers.
- Rooms/venues, where applicable.
- Periods and break times.
- Academic days.
- Effective dates.

Validate:

- Teacher double-booking.
- Class/arm double-booking.
- Room conflicts.
- Unavailable periods.
- Teacher workload limits where configured.

Allow authorized users to view, print and export timetables. Keep historical timetable versions.

# 14. Attendance Management

Support attendance for students and staff.

Student attendance should support:

- Present.
- Absent.
- Late.
- Excused.
- Approved leave, if configured.

Requirements:

- Daily and lesson-based attendance options.
- Attendance by class/arm and timetable period.
- Authorized corrections with reasons.
- Parent notifications for configured events.
- Attendance summaries by student, class, term and session.
- Attendance reports and export.
- Audit trail for changes.

Biometric attendance is a later integration, not a prerequisite for the MVP.

# Student and Staff Identity Card Management

Develop a dedicated Identity Card Management Module integrated with Student Management, Admissions, Employee/HR Management and Institution Settings.

## 1. Student ID Card Management

The system must automatically generate a student identity card using the student's existing biodata.

Required information:
- School name and logo.
- Student passport photograph.
- Full name.
- Unique student admission/identification number.
- Date of birth, where institution policy permits.
- Class and arm.
- Campus.
- Academic session.
- Issue date.
- Expiry date.
- QR code or barcode for identity verification.

Requirements:
- Automatically populate card information from the student's existing profile.
- Allow authorized users to preview and generate individual or bulk student ID cards.
- Support card generation following successful admission and enrolment.
- Allow regeneration when a student changes class, photograph or other approved card information.
- Maintain ID card issuance history.
- Support replacement cards for lost or damaged cards.
- Allow authorized administrators to deactivate or revoke an ID card.
- Maintain previous card records and prevent duplicate active cards where school policy requires one active card per student.

## 2. Staff ID Card Management

Generate staff identity cards from existing employee records.

Required information:
- School name and logo.
- Staff passport photograph.
- Full name.
- Unique employee/staff identification number.
- Job title/designation.
- Department.
- Campus.
- Employment category, where appropriate.
- Issue date.
- Expiry date.
- QR code or barcode for identity verification.

Requirements:
- Automatically retrieve staff biodata from the employee profile.
- Support individual and bulk card generation.
- Generate cards after staff onboarding and approval.
- Allow authorized updates and replacement cards.
- Deactivate cards when employment ends, where applicable.
- Preserve card issuance and replacement history.
- Restrict staff personal information displayed on cards to approved fields.

## 3. ID Card Design and Template Management

Provide an ID card design interface for authorized administrators.

Allow configuration of:
- School logo.
- School name and contact details.
- Primary and secondary brand colours.
- Card background and layout.
- Portrait or landscape orientation.
- Front and back card designs.
- Font style and size.
- Field visibility and positioning.
- QR code/barcode placement.
- Signature and authorized signatory, where required.
- Issue and expiry date formats.

Provide separate templates for students and staff. Support multiple campuses and optional department-specific templates.

## 4. Card Generation and Printing

The system must support:
- Individual card generation.
- Bulk card generation by class, arm, campus, department or staff category.
- PDF output.
- Print-ready layouts with accurate card dimensions.
- Standard CR80 card size (85.60 mm × 53.98 mm), with configurable alternatives.
- Front and back card printing.
- Multiple cards arranged on an A4 print sheet.
- High-resolution photographs and logos.
- Print preview before final printing.
- Reprint and replacement workflows.

Ensure that the generated PDF preserves the card dimensions and layout when printed.

## 5. QR Code and Identity Verification

Generate a unique QR code for each issued identity card.

When scanned, the QR code should open a secure verification page or endpoint showing only approved information, such as:
- Cardholder's name.
- Photograph, if permitted.
- Student or staff identification number.
- Card category.
- Institution/campus.
- Card status: Active, Expired or Revoked.
- Card validity dates.

Security requirements:
- Never encode sensitive biodata directly in the QR code.
- Use a random, non-guessable verification token or secure identifier.
- Do not expose addresses, phone numbers, medical details or confidential employee information.
- Allow authorized administrators to revoke compromised or replaced cards.
- Ensure expired and revoked cards cannot be verified as active.

## 6. ID Card Status and Issuance Workflow

Support the following lifecycle:

Draft → Generated → Approved → Issued → Active → Expired / Revoked / Replaced

Maintain:
- Card reference number.
- Cardholder reference.
- Card type.
- Template version.
- Issue date.
- Expiry date.
- Issued by.
- Approval details, where required.
- Replacement reason.
- Revocation reason.
- Previous card reference.

All issuance, replacement, approval and revocation activities must be auditable.

## 7. Access Control

Provide permissions for:
- View ID card records.
- Configure templates.
- Generate individual cards.
- Generate bulk cards.
- Approve card issuance.
- Print cards.
- Replace cards.
- Revoke cards.
- Access verification reports.

Only authorized personnel may generate or approve official cards.

## 8. Acceptance Criteria

The module is complete when:
1. A student ID card can be generated from an existing student profile without re-entering biodata.
2. A staff ID card can be generated from an existing employee profile.
3. The system supports individual and bulk card generation.
4. Administrators can configure separate student and staff templates.
5. Cards can be exported as print-ready PDFs using the configured dimensions.
6. Cards can be printed individually or arranged on A4 sheets.
7. QR codes can verify card authenticity and current status.
8. Lost, damaged, expired or replaced cards can be revoked or deactivated.
9. Card issuance and replacement history is preserved.
10. All card management operations enforce role-based permissions and audit logging.

# 15. Examinations, Continuous Assessment and Results

Build a complete, configurable examination and result-management module.

## Assessment configuration

Allow the institution to define:

- Continuous assessment components.
- Tests, assignments, practicals and projects.
- Examination component.
- Maximum marks and weighting.
- Assessment dates.
- Applicable session, term, class, arm and subject.
- Grading scheme and effective date.

Do not hardcode one universal grading structure. Support different grading schemes by school level or academic period.

## Result entry

- Subject teachers may enter marks only for their assigned subject/class/arm.
- Validate marks against the maximum permitted score.
- Support draft saving and bulk entry with clear validation feedback.
- Identify missing, invalid or out-of-range marks.
- Prevent duplicate result records for the same student, subject, assessment and academic period unless the assessment design explicitly permits multiple attempts.
- Record the user and timestamp for every submission or correction.

## Result workflow

Implement a controlled workflow such as:

`Draft → Submitted → Returned for Correction → Resubmitted → Approved → Published`

The institution may configure the review stages, but permissions and audit requirements must remain enforced.

Rules:

- Teachers cannot approve their own results unless an explicitly authorized policy permits it.
- Published/approved results must not be silently edited.
- Corrections after approval must use a formal correction request.
- A correction must record the reason, original value, revised value, requester, reviewer, approver and timestamps.
- Recalculate affected totals, grades, positions and report cards only through controlled services.
- Preserve previous published versions for audit purposes.
- Do not publish incomplete results as final.

## Result calculations

Support configurable:

- Assessment weighting.
- Total score.
- Grade boundaries.
- Grade descriptions.
- Remarks.
- Class/subject averages.
- Position/ranking, if the institution uses ranking.
- Promotion eligibility rules.
- Pass/fail thresholds.
- Behaviour, effort or skills indicators where configured.

Clearly document rounding rules and tie-handling rules. Never assume ranking is required by every institution.

# 16. Student Report Cards

Generate professional report cards using approved and published academic data.

A report card may include:

- School identity, logo and contact information.
- Student name, admission number and photograph.
- Class, arm, session and term.
- Subject scores and grades.
- Continuous assessment and examination breakdown.
- Total and average.
- Position/rank only if enabled.
- Attendance summary.
- Teacher remarks.
- Class teacher remarks.
- Principal/head teacher remarks.
- Promotion status, where applicable.
- Grading legend.
- Authorized signatures or approval details.

Requirements:

- Generate PDF reports.
- Support individual and authorized bulk generation.
- Use a consistent, configurable template.
- Do not expose draft or unapproved results on official report cards.
- Record generation and publication events.
- Restrict access to authorized users, parents and students.

# 17. Cumulative Student Transcript Management

This is a mandatory core capability.

The system must generate a student's cumulative academic transcript using approved historical results across all completed academic sessions and terms.

## Transcript content

Include, as applicable:

- Institution name, logo and address.
- Student full name.
- Admission/student number.
- Date of birth, if institution policy permits.
- Programme or school level.
- Admission and graduation dates.
- Classes/grades attended.
- Academic sessions and terms.
- Subjects taken in each period.
- Scores, grades and grade descriptions.
- Credit units, only where the institution uses them.
- Cumulative averages or GPA, only where the institution has defined a valid calculation method.
- Graduation/completion status.
- Authorized signatory and issue date.
- Unique transcript reference number.
- Verification instructions and QR code or secure verification URL.

## Transcript rules

- Only approved and published results may appear on an official transcript.
- The transcript must draw on historical records, not only the student's current class.
- Preserve the grading scheme that applied when each result was earned.
- Do not recalculate historical grades using a newly introduced grading scale.
- If records are incomplete, clearly label the document as provisional or prevent official issuance according to school policy.
- Official transcripts must have a unique reference number.
- Generate a PDF suitable for printing and secure sharing.
- Maintain a record of every transcript issued, by whom, to whom, when and for what purpose.
- Support transcript reissue and correction with version history.
- A correction must not erase the previous issued version.
- Provide a secure verification page or endpoint that confirms document authenticity without exposing unnecessary personal information.
- Use expiring or access-controlled download links for private documents.

## Transcript approval workflow

Suggested workflow:

`Requested → Under Review → Approved → Generated → Issued`

A transcript correction should follow a separate authorized process and retain the prior issue record.

# 18. Student Promotion, Graduation and Alumni

## Promotion and graduation

Support configurable promotion decisions based on institution policy.

- Promote students individually or in batches.
- Support repetition, transfer, withdrawal and graduation.
- Validate outstanding academic requirements where configured.
- Preserve the student's complete academic history.
- Record approval, effective date and responsible officer.

## Alumni management

Keep Alumni Management as a defined module.

At graduation:

- Preserve the original student record.
- Create or activate a linked alumni profile.
- Retain admission number and historical academic records.
- Record graduation session, class and relevant qualifications.
- Do not create a disconnected duplicate person record.

Release 2 alumni capabilities may include:

- Alumni directory with privacy controls.
- Alumni portal and profile updates.
- Alumni events and reunions.
- Alumni communication.
- Mentorship and career networking.
- Donations and fundraising.
- Employment and further-study updates.
- Alumni association management.
- Transcript and certificate request workflows.

# 19. Finance: Fees, Invoices and Payments

The MVP must provide reliable basic school fee management. Full double-entry accounting may be delivered in Release 2, but the MVP must be designed so that financial transactions can later integrate with a proper ledger.

## Fee management

Support:

- Fee categories.
- Fee schedules by class, campus, session and term.
- Compulsory and optional charges.
- Discounts, scholarships and bursaries.
- Installment plans.
- Due dates.
- Authorized waivers and adjustments.
- Student account statements.

## Invoices and payments

Support:

- Invoice generation.
- Full and partial payments.
- Payment methods.
- Receipts.
- Payment allocation to outstanding invoices.
- Overpayments and credit balances.
- Refunds and reversals through controlled workflows.
- Outstanding balances and ageing reports.
- Financial exports and reconciliation.

Rules:

- Never mark an invoice paid merely because a user returned from a payment page.
- Verify gateway payments through authenticated server-side callbacks or reconciliation.
- Use idempotency controls to prevent duplicate payment posting.
- Record transaction references and gateway responses safely.
- Reversals and refunds require authorization and an audit trail.
- Do not delete posted financial transactions; use reversal/adjustment entries.
- Store the currency on the transaction and invoice. NGN is the default.
- Design for future multi-currency support without silently mixing currencies.

## Accounting extension

Release 2 should include a proper double-entry accounting system with:

- Chart of accounts.
- General ledger.
- Journal entries.
- Accounts receivable.
- Accounts payable.
- Bank and cash accounts.
- Trial balance.
- Income statement.
- Balance sheet.
- Cash flow reporting.
- Period closing and controlled journal reversal.

Do not label a basic income/expense list as a complete accounting system.

# 20. HR and Payroll

The employee module should maintain staff records in the MVP. Full HR and payroll may be implemented in Release 2.

Potential capabilities:

- Employee profiles and employee numbers.
- Departments and job titles.
- Employment type and status.
- Contracts and documents.
- Leave and absence.
- Attendance.
- Payroll structure.
- Allowances and deductions.
- Payslips.
- Payroll approval and payment records.

Payroll must use configurable, effective-dated rules. Do not hardcode tax rates, pension rates, statutory thresholds or legal requirements. Provide a controlled way for authorized personnel to update rules when laws change. Include effective dates, approval history and calculation traceability. Require review by qualified local payroll/accounting personnel before production use.

# 21. Parent, Student and Teacher Portals

Provide role-specific portals using the same backend data and authorization rules.

## Parent portal

Parents/guardians may, according to permissions:

- View linked student profiles.
- View attendance.
- View approved report cards and results.
- View fee invoices, receipts and balances.
- Receive school announcements.
- View timetables and calendars.
- Submit enquiries or requests.
- Update permitted contact information.

## Teacher portal

Teachers may:

- View assigned classes and subjects.
- View teaching timetable.
- Mark attendance for authorized classes.
- Enter and submit results for assigned subjects.
- View result submission status.
- View relevant student information.
- Receive school announcements.

## Student portal

If enabled:

- View own timetable.
- View own attendance.
- View published results and report cards.
- View assignments or learning resources when LMS is enabled.
- Receive school announcements.

## Alumni portal

Full portal capabilities may be delivered in Release 2. Alumni access must remain separate from active student access and must respect privacy settings.

# 22. Public Website and Integrated CMS

Build a public-facing school website that is managed from the same platform through a secure CMS.

Suggested public pages:

- Home.
- About the School.
- Mission, Vision and Values.
- History and Leadership.
- Academics.
- Nursery, Primary and Secondary sections.
- Admissions.
- Admission requirements and process.
- School facilities.
- News and Announcements.
- Events and Calendar.
- Gallery.
- Staff/Leadership profiles, where approved for publication.
- Contact Us.
- Frequently Asked Questions.
- Policies and downloadable documents.
- Privacy Policy and Terms.

CMS capabilities:

- Create, edit, preview, schedule and publish pages.
- Draft, review and publish workflow.
- Manage navigation menus.
- Upload and manage images/documents.
- Configure homepage sections.
- Manage news, announcements and events.
- Configure SEO title, description and social sharing metadata.
- Set page slugs and redirects.
- Archive or unpublish content.
- Maintain content revision history.
- Restrict CMS permissions by role.
- Keep public website content separate from private student and staff records.

The CMS must never expose private ERP data through public endpoints. Use explicit publication status and approved public fields only.

# 23. Communications and Notifications

Provide a centralized communication module.

Channels may include:

- In-app notifications.
- Email.
- SMS.
- WhatsApp Business integration in a later release.

Support:

- Templates.
- Recipient targeting by role, campus, class, parent or student.
- Delivery status.
- Retry and failure logging.
- Communication preferences and consent.
- Announcement scheduling.
- Audit history for important communications.

Avoid sending sensitive student information through insecure channels. Provide links to authenticated portals where appropriate.

# 24. Inventory, Asset Management, Procurement, Library, Transport and Hostel

Inventory, asset management and procurement must be treated as distinct but integrated business capabilities. Inventory controls consumable and stock-managed items; asset management controls durable school-owned assets; procurement manages the approved purchasing process that may create either inventory receipts or new asset records. These modules should follow the same architecture, permissions, audit and approval standards as the rest of the ERP.

## 24.1 Inventory and Stores Management

Support the complete stock lifecycle for teaching materials, stationery, office supplies, cleaning materials, uniforms, sports equipment, laboratory consumables, maintenance materials and other school supplies.

Core capabilities:

- Item catalogue with unique item code/SKU, item name, description, category, unit of measure and optional barcode/QR code.
- Item types such as consumable, stock-managed, non-stock, and asset-controlled; prevent the same item from being ambiguously treated as both consumable stock and a serialized asset.
- Multiple stores, stockrooms, campuses and storage locations.
- Opening stock and approved stock receipt.
- Goods received notes (GRNs) linked to purchase orders where applicable.
- Stock issue/requisition to departments, teachers, classrooms, laboratories, maintenance teams or other authorized cost centres.
- Stock transfers between stores and campuses.
- Returns to store and supplier returns.
- Stock adjustments with mandatory reason and approval.
- Physical stock counts and reconciliation against system balances.
- Minimum/maximum stock levels and reorder alerts.
- Batch/lot and expiry-date tracking for items where relevant, such as laboratory or health-related consumables.
- Stock valuation method configurable by the institution and reviewed by its accountant; do not silently mix valuation methods.
- Stock movement ledger showing opening balance, receipts, issues, transfers, returns and adjustments.
- Reports for stock on hand, stock movement, low stock, stock valuation, consumption by department and stock discrepancies.

Inventory controls:

- Do not allow negative stock by default. Any exception must be an explicit, permission-controlled policy and fully audited.
- Every stock movement must be recorded as a transaction; do not directly overwrite stock balances without a corresponding movement record.
- Use database transactions and concurrency-safe updates to prevent two users from issuing the same available stock.
- Posted stock transactions must be reversed or adjusted through controlled transactions, not deleted.
- Restrict stock visibility and operations by institution, campus and store.
- Require authorization for high-value issues, adjustments, write-offs and inter-campus transfers according to configurable thresholds.

## 24.2 Asset Management

Maintain a central register of durable school-owned assets, including computers, printers, projectors, furniture, laboratory equipment, generators, air conditioners, vehicles, networking equipment, security/CCTV equipment and other property.

Each asset record should support:

- Unique asset identification number generated from a configurable pattern.
- Asset name, description, category and asset type.
- Manufacturer, model, serial number and barcode/QR tag where available.
- Acquisition date, supplier, purchase order and acquisition cost.
- Funding source or project reference, if applicable.
- Campus, building, room or physical location.
- Assigned department, responsible employee/custodian and current user, where relevant.
- Asset condition: new, good, fair, damaged, under repair or beyond repair.
- Asset status: in store, available, assigned, under maintenance, missing, disposed or retired.
- Warranty provider, warranty start/end dates and supporting documents.
- Insurance details, where applicable.
- Photographs, invoices, manuals and other attachments.
- Expected useful life and residual value, where depreciation is required.
- Maintenance history, inspection history and movement history.
- Disposal date, disposal method, approval and proceeds, where applicable.

Asset lifecycle:

`Requested → Procured → Received/Registered → Available → Assigned → Under Maintenance / Returned / Transferred → Retired / Disposed`

Requirements:

- Register assets individually where serial-level tracking is required.
- Generate printable asset tags with QR/barcode identifiers.
- Record handover and return acknowledgements for assigned assets.
- Maintain a complete custody and location history; changing the current custodian must not erase previous assignments.
- Support periodic physical verification and reconciliation, including missing, damaged and unlocated assets.
- Record maintenance requests, work orders, service providers, costs, dates and outcomes.
- Support preventive maintenance schedules and reminders.
- Track warranty expiry and maintenance due dates.
- Support configurable depreciation methods and asset classes if accounting policy requires it. Depreciation calculations must be reviewed and approved by the institution's accountant and must integrate with the general ledger when that module is available.
- Require authorized approval for asset write-off, retirement and disposal.
- Do not treat asset depreciation as a simple stock adjustment.

## 24.3 Procurement and Supplier Management

Provide a controlled purchasing workflow:

`Purchase Requisition → Departmental Review → Budget/Finance Check → Approval → Request for Quotation (if required) → Supplier Selection → Purchase Order → Goods Received → Invoice Matching → Payment Processing`

Capabilities:

- Supplier/vendor profiles, contacts, addresses, tax/business details where required, bank/payment details with restricted access, and supplier status.
- Departmental purchase requisitions with item, quantity, specification, justification, estimated cost, required date and delivery location.
- Configurable approval limits by amount, department, campus and role.
- Budget availability checks where budgeting is enabled.
- Supplier quotations and comparison records.
- Purchase order generation, numbering, approval and amendment history.
- Goods received notes with accepted, rejected, damaged and outstanding quantities.
- Partial deliveries and backorders.
- Supplier invoice capture and matching against purchase orders and goods received records.
- Supplier returns and purchase order cancellation.
- Procurement reports by supplier, category, department, campus, period and status.

Procurement controls:

- Separate requisition, approval, receipt and payment permissions where practical.
- Prevent users from approving their own requests when segregation of duties is configured.
- Do not automatically mark an order as received or paid based only on a user interface action.
- Record approval decisions, reasons, timestamps and supporting documents.
- Apply duplicate invoice/reference checks and maintain an audit trail.
- Integrate accepted goods with inventory receipts or asset registration, depending on item type.

## 24.4 Integration Between Procurement, Inventory, Assets and Finance

The modules must share consistent references while maintaining clear ownership:

- An approved purchase order may contain stock items, asset items or both.
- Receipt of consumable stock creates inventory receipt transactions and updates stock balances.
- Receipt of serialized durable equipment creates or completes individual asset records; it must not simply increase consumable stock.
- Supplier invoices are matched to purchase orders and goods received records before payment approval, subject to configured policy.
- Finance records supplier liabilities and payments. Inventory and asset modules provide the operational evidence and references; they must not create a second, conflicting financial ledger.
- When the general ledger is introduced, approved stock and asset transactions may post accounting entries through a documented integration service.
- Maintain traceability from requisition to purchase order, receipt, inventory movement or asset record, supplier invoice and payment.

## 24.5 Library Management

These modules are planned extensions and should follow the same architecture and security standards.

## Library

- Book catalogue.
- Categories and authors.
- Copies and barcode/identifier.
- Borrowing and returns.
- Renewals and reservations.
- Overdue tracking and fines, if enabled.
- Student/staff borrowing history.

## Inventory and procurement

- Item catalogue.
- Stock locations.
- Suppliers.
- Purchase requests.
- Approval workflow.
- Purchase orders.
- Goods received.
- Stock movements.
- Reorder alerts.
- Asset register and maintenance history.

## Transport

- Vehicles.
- Drivers and attendants.
- Routes and stops.
- Student route assignments.
- Transport fees.
- Vehicle maintenance.
- Optional GPS integration later.

## Hostel/boarding

- Hostels and rooms.
- Bed allocation.
- Student occupancy.
- Check-in/check-out.
- Boarding attendance.
- House parent/warden records.
- Maintenance and incident reporting.

# 25. Dashboards, Reporting and Analytics

Create role-specific dashboards.

Examples:

- Total active students.
- Inventory stock value and quantity on hand by campus/store.
- Low-stock and reorder alerts.
- Stock issues and consumption by department.
- Asset register totals by category, campus, condition and status.
- Assets assigned to staff/departments and assets awaiting return.
- Assets due for maintenance, warranty expiry or physical verification.
- Procurement spend, pending requisitions, purchase orders and supplier delivery performance.
- Total active students.
- Admissions by status.
- Enrolment by class, arm and campus.
- Student attendance rates.
- Teacher attendance.
- Subject and class performance.
- Result submission and approval status.
- Students at academic risk, based on transparent configurable rules.
- Fees billed, collected and outstanding.
- Payment trends.
- Staff summary.
- Website enquiries and admissions conversion.

Reporting requirements:

- Filters by institution, campus, session, term, class, arm and date.
- Export to PDF and Excel/CSV where appropriate.
- Respect all permissions and data scopes.
- Use asynchronous processing for large reports.
- Record who generated sensitive exports.
- Avoid exposing personal information in aggregate dashboards unnecessarily.

# 26. Data Model and Identifier Rules

Create an ERD and data dictionary before implementing the full domain.

Use stable internal primary keys, preferably UUIDs where appropriate. Human-readable identifiers must be generated separately and must not depend on names.

Provide configurable identifier patterns for:

- Student admission number.
- Employee number.
- Applicant/application number.
- Alumni number, if required.
- Invoice number.
- Receipt number.
- Transcript reference number.
- Payment reference.
- Item/SKU code.
- Asset tag/asset number.
- Purchase requisition number.
- Purchase order number.
- Goods received note number.
- Stock issue/transfer/adjustment reference.
- Supplier invoice reference.

Define sequence scope explicitly, such as institution, campus, admission year or financial year. Enforce uniqueness at the database level. Once issued, official identifiers should be immutable except through a controlled administrative correction process.

Use appropriate:

- Foreign keys.
- Unique constraints.
- Check constraints.
- Indexes.
- Transaction boundaries.
- Historical/effective-dated records.
- Created/updated timestamps.
- Created-by/updated-by references where appropriate.

Do not store derived values redundantly unless there is a documented reason and a reliable recalculation strategy.

# 27. Data Validation, Imports and Migration

Provide controlled CSV/Excel import tools for authorized users.

Requirements:

- Downloadable templates.
- Field validation.
- Duplicate detection.
- Preview before import.
- Dry-run mode.
- Row-level error reports.
- Import summary.
- Transaction-safe processing where feasible.
- Audit record of imports.
- No silent partial imports.

Provide a documented data migration strategy for existing student, staff, academic and finance records. Preserve source references and migration logs.

# 28. Privacy, Security and Audit

Treat student, guardian, staff, medical, academic and financial information as sensitive institutional data.

Requirements:

- Least-privilege access.
- Institution/campus/record-level authorization.
- TLS for network traffic.
- Encryption at rest through supported infrastructure/database/storage controls.
- Secure secrets management.
- Input validation and output encoding.
- Protection against CSRF, XSS, SQL injection, SSRF and insecure direct object references.
- Rate limiting for sensitive endpoints.
- Secure file upload validation.
- Malware scanning integration point for uploaded files.
- Private object storage for confidential documents.
- Expiring signed URLs for authorized file downloads.
- No sensitive data in application logs.
- Audit logging for sensitive operations.
- Regular dependency and vulnerability checks.

## Audit events

At minimum, record:

- Login and security events.
- User and role changes.
- Permission changes.
- Student record changes.
- Teacher allocation changes.
- Attendance corrections.
- Result entry, submission, approval, publication and correction.
- Report card and transcript generation/issuance.
- Invoice, payment, refund and reversal events.
- CMS publication changes.
- Data exports and bulk imports.

Audit records should identify actor, action, target, timestamp, reason where relevant, and a safe summary of the change. Prevent ordinary users from editing or deleting audit records.

## Privacy and retention

- Define data categories and access rules.
- Configure retention periods by record type and legal requirement.
- Support authorized data access/correction requests.
- Apply anonymization or deletion only where lawful and approved.
- Preserve official academic and financial records where retention obligations apply.
- Restrict medical and welfare information to specifically authorized roles.
- Obtain and record consent where required for communications and optional data use.

# 29. File and Document Management

Support secure upload and storage for:

- Student photographs.
- Admission documents.
- Certificates.
- Staff documents.
- Receipts and financial attachments.
- Report cards and transcripts.
- CMS images and public documents.

Requirements:

- Validate file extension, MIME type and file size.
- Generate safe storage names.
- Store private documents outside public web roots.
- Use private object storage or protected media delivery.
- Use expiring signed URLs or authenticated download endpoints.
- Scan uploaded files for malware where infrastructure supports it.
- Apply role and record-level access checks to every download.
- Keep document metadata and audit history.
- Separate public CMS media from confidential ERP documents.

# 30. Third-Party Integrations

Use an adapter/service pattern so providers can be changed without rewriting core business logic.

Potential integrations:

- Payment gateways.
- Email providers.
- SMS providers.
- WhatsApp Business.
- Biometric devices.
- GPS/transport tracking.
- Identity or document verification services.

Integration requirements:

- Keep API credentials in environment variables or a secrets manager.
- Validate webhook signatures.
- Use idempotency keys.
- Implement retries with exponential backoff.
- Record delivery and processing outcomes.
- Provide failed-event inspection and replay controls.
- Implement reconciliation for payments.
- Never trust a client-side success redirect as proof of payment.
- Document provider-specific assumptions and failure modes.

Do not select a payment, SMS or email provider without confirming the institution's requirements, region, cost and available credentials.

# 31. Non-Functional Requirements

Establish measurable targets and validate them through testing. Initial targets for planning:

| Area | Initial target |
|---|---|
| Standard API/page response | 95% of ordinary requests under 2 seconds under an agreed test load |
| Initial load test | At least 100 concurrent users, subject to agreed deployment hardware |
| Report generation | Typical individual report/transcript under 10 seconds |
| Bulk exports | Asynchronous background processing with progress/status |
| Availability | 99.5% monthly target, excluding agreed planned maintenance |
| Recovery Point Objective | 24 hours or better |
| Recovery Time Objective | 8 hours or better |
| Backup | Automated daily backup; point-in-time recovery where supported |
| Restore testing | At least quarterly |
| Accessibility | Target WCAG 2.2 AA |
| Browser support | Current and previous major versions of Chrome, Edge, Firefox and Safari |
| Mobile | Responsive support for modern Android and iOS browsers |

These are initial service objectives, not guarantees. Validate them against actual infrastructure, data volume and load-test results.

Additional requirements:

- Consistent UI and predictable navigation.
- Responsive desktop, tablet and mobile layouts.
- Accessible forms, controls, contrast and keyboard navigation.
- Pagination and filtering for large datasets.
- Database query optimization and indexes.
- Caching only where data freshness and authorization are preserved.
- Background jobs for bulk work.
- Graceful error handling and useful user feedback.
- Configurable locale, timezone, currency and date formatting.

# 32. Testing and Quality Assurance

Testing is mandatory, not optional.

## Backend tests

- Model and validation tests.
- Service/business logic tests.
- API tests.
- Permission and scope tests.
- Workflow/state-transition tests.
- Financial calculation tests.
- Result and transcript calculation tests.
- Integration and webhook tests.
- Database constraint tests.

## Frontend tests

- Component tests.
- Form validation tests.
- Routing and protected-page tests.
- Role-based UI tests.
- API error and loading-state tests.
- Accessibility checks.

## End-to-end tests

Cover critical journeys:

1. Applicant enquiry through admission and enrolment.
2. Student assignment to campus, class and arm.
3. Subject creation and teacher allocation.
4. Teacher attendance marking.
5. Teacher result entry and submission.
6. Result review, approval and publication.
7. Parent viewing an approved report card.
8. Cumulative transcript generation and verification.
9. Fee invoice creation and payment reconciliation.
10. Student graduation and alumni linkage.
11. CMS content approval and publication.
12. Unauthorized user attempting to access another campus or student's records.

Aim for at least 80% coverage of critical business logic, but prioritize meaningful tests over a misleading overall percentage. Include negative authorization tests for every sensitive workflow.

# 33. DevOps, Monitoring, Backup and Recovery

Provide:

- Reproducible local setup.
- Separate development, staging and production configurations.
- CI checks for formatting, linting, type checking, tests and builds.
- Secure production environment configuration.
- Database migration and rollback guidance.
- Application and background-worker health checks.
- Structured logs with correlation/request IDs.
- Error monitoring and alerting.
- Database and media backups.
- Documented restoration procedure.
- Periodic restore tests.
- Deployment and release checklist.
- Incident response and rollback guidance.

Never treat a successful backup job as proof that recovery works. Test restoration.

# 34. UI/UX and Design Standards

Create a professional, modern school administration interface.

Design principles:

- Clear information hierarchy.
- Consistent navigation and page structure.
- Role-specific dashboards.
- Readable tables with search, filters, sorting and pagination.
- Clear forms with inline validation.
- Confirmation for destructive or irreversible actions.
- Accessible colour contrast and keyboard navigation.
- Responsive layouts.
- Consistent status labels and feedback.
- Useful empty, loading, success and error states.
- Printable reports and documents.
- Avoid clutter, excessive gradients and unnecessary animations.

The public website should have a distinct public-facing visual experience while sharing the institution's branding and CMS content with the administrative platform.

Allow authorized administrators to configure:

- School logo.
- School name and contact details.
- Primary and secondary brand colours.
- Website theme settings.
- Public website assets.
- Report card and transcript branding.

Brand settings must not undermine accessibility or readability.

# 35. Glossary and Domain Consistency

Use consistent terminology throughout the database, API, frontend and documentation.

- **Institution/School:** The organization operating the platform.
- **Campus:** A physical branch/location of the institution.
- **Academic session/year:** The full academic cycle.
- **Term/Semester:** A division of the academic session.
- **Class/Grade:** The academic level a student attends.
- **Arm/Section:** A subdivision of a class.
- **Subject:** A course or learning area offered to a class.
- **Subject teacher:** A teacher assigned to teach a specific subject to a class/arm.
- **Class teacher:** A teacher responsible for the general administration of a class/arm.
- **Continuous Assessment (CA):** Non-final assessment components defined by school policy.
- **Result/Broadsheet:** A structured record or summary of student assessment outcomes.
- **Report card:** A term/session performance report.
- **Transcript:** An official cumulative record of approved academic performance.
- **Alumni:** A former student, usually linked to a completed/graduated student record.

Do not use these terms interchangeably in code or documentation.

# 36. Implementation Roadmap

Work in controlled phases. Each phase must have a reviewable deliverable and passing tests before moving to the next.

## Phase 0 — Discovery and architecture

Deliver:

- Requirements and decisions register.
- MVP scope confirmation.
- Domain glossary.
- Architecture decision records (ADRs).
- ERD and initial data dictionary.
- Module ownership map.
- RBAC permission matrix.
- Key workflow/state diagrams.
- API conventions and OpenAPI plan.
- Deployment and environment plan.

Do not begin broad feature coding before the domain model and critical workflows are reviewed.

## Phase 1 — Foundation

Implement:

- Repository and project structure.
- Backend and frontend foundations.
- Environment configuration.
- Institution and campus context.
- Authentication.
- RBAC.
- Audit framework.
- CI pipeline.
- Base UI system.
- Initial automated tests.

## Phase 2 — Student and admissions

Implement:

- Enquiries.
- Applications.
- Admissions.
- Student profiles.
- Guardian relationships.
- Student lifecycle.
- Document management.

## Phase 3 — Academic and teaching

Implement:

- Academic sessions and terms.
- Classes and arms.
- Subjects.
- Teacher and employee records.
- Subject teacher allocation.
- Timetables.
- Attendance.

## Phase 4 — Examinations and transcripts

Implement:

- Assessment configuration.
- Result entry and validation.
- Submission and approval workflow.
- Result publication.
- Report cards.
- Cumulative transcripts.
- Transcript verification.
- Graduation and alumni linkage.

## Phase 5 — Finance and portals

Implement:

- Fee schedules.
- Invoices.
- Payments and reconciliation.
- Receipts and balances.
- Parent portal.
- Teacher portal.
- Notifications.

## Phase 6 — Public website and CMS

Implement:

- Public website.
- CMS pages and navigation.
- News, events and gallery.
- Content approval and publication.
- SEO and metadata.
- Public/private content separation.

## Phase 7 — Hardening and production readiness

Complete:

- Security review.
- Performance and load testing.
- Accessibility checks.
- Backup/restore test.
- Data import validation.
- User acceptance testing.
- Deployment documentation.
- Administrator and user guides.
- Production release checklist.

Only after the MVP is stable should Release 2 modules begin.

# 37. AI Development Agent Operating Instructions

You are the lead software architect and senior full-stack engineering agent responsible for implementing this project.

Follow these rules:

1. Inspect the existing repository before making changes.
2. If the repository already contains code, preserve working functionality and identify existing conventions before refactoring.
3. Do not overwrite or delete files without understanding their purpose.
4. Begin with Phase 0 deliverables and present the architecture and domain decisions for review.
5. Maintain a clear implementation plan and update it as work progresses.
6. Implement one module or vertical workflow at a time.
7. Build complete workflows, not disconnected screens.
8. Enforce business rules on the backend; frontend validation is supplementary.
9. Use database constraints and transactions for critical operations.
10. Use service-layer functions for complex calculations and state transitions.
11. Do not duplicate business logic across API views, serializers and frontend components.
12. Use migrations for schema changes.
13. Add tests with every significant feature.
14. Test both authorized and unauthorized access.
15. Keep API documentation and project documentation current.
16. Use realistic seed/demo data only in non-production environments.
17. Do not hardcode institution-specific grading, fee, payroll, tax or calendar rules.
18. Do not expose confidential records through public website endpoints.
19. Do not claim a feature is complete unless the code, tests and documented acceptance criteria support that claim.
20. Report known limitations, incomplete work, assumptions and security concerns honestly.

For each implementation phase, report:

- What was implemented.
- Files and modules changed.
- Database migrations created.
- API endpoints added or changed.
- Permissions and business rules enforced.
- Tests executed and their results.
- Known limitations or outstanding decisions.
- How to run and verify the feature.

# 38. MVP Acceptance Criteria

The MVP is not complete until the following end-to-end scenarios work:

## Student and admissions

- An authorized admissions user can create an enquiry and application.
- An application can be reviewed and approved.
- An accepted applicant can be enrolled without duplicate identity records.
- A unique admission number is generated and protected by a database constraint.
- A parent/guardian can be linked to one or more students.

## Academic and subject teacher allocation

- An administrator can create sessions, terms, classes, arms and subjects.
- An administrator can assign a subject teacher to a subject, class and arm.
- One teacher can have multiple valid assignments.
- The system detects relevant timetable and allocation conflicts.
- A teacher cannot enter results for an unassigned subject/class/arm unless separately authorized.

## Results and report cards

- An assigned subject teacher can enter and submit marks.
- Invalid marks are rejected with useful feedback.
- Results follow the configured review and approval workflow.
- Approved results cannot be silently edited.
- Corrections retain before/after values and approval history.
- Only approved/published results appear on official report cards.

## Cumulative transcripts

- The system retrieves approved historical results across academic sessions.
- Historical grading rules are preserved.
- An authorized officer can approve and issue an official transcript.
- Each transcript has a unique reference.
- The generated PDF is printable and contains the configured school/student details.
- A verification process confirms authenticity without exposing unnecessary private data.
- Reissued or corrected transcripts preserve prior issue history.

## Finance

- An authorized user can configure fees and create an invoice.
- Full and partial payments can be recorded.
- Duplicate payment callbacks do not create duplicate transactions.
- Receipts and balances are accurate.
- Refunds and reversals require authorization and retain an audit trail.

## Portals and CMS

- A parent can see only their linked students and permitted information.
- A teacher can see only assigned classes/subjects and permitted student data.
- Authorized CMS staff can draft, review and publish public pages.
- Draft or private ERP records are never publicly accessible.

## Inventory, asset and procurement

- An authorized user can create an item and maintain stock by campus/store.
- Receiving purchased stock creates a traceable stock movement and updates the correct balance.
- Issuing stock reduces the available balance and records the recipient, purpose and authorizing user.
- Concurrent issues cannot cause an unapproved negative stock balance.
- A stock adjustment requires a reason and the configured approval.
- A durable asset can be registered with a unique asset tag, location, custodian, condition and status.
- Asset handovers, returns, transfers, maintenance and disposal preserve full history.
- An approved purchase order can be received partially or fully, with discrepancies recorded.
- A received consumable is routed to inventory; a serialized durable item is routed to the asset register.
- Procurement, inventory, asset and finance records are traceable without duplicate ledger postings.

## Security and operations

- Unauthorized cross-campus and cross-institution access is denied.
- Sensitive actions create audit records.
- Automated tests cover critical workflows and permission boundaries.
- Backup restoration has been demonstrated in a test environment.
- Deployment and setup instructions are complete.

# 39. Final Delivery Requirements

Deliver a maintainable, documented and tested application, including:

- Complete source code.
- Database schema and migrations.
- ERD and data dictionary.
- OpenAPI/API documentation.
- Installation and environment setup guide.
- `.env.example` without real secrets.
- Docker configuration.
- Test suite and test instructions.
- Deployment guide.
- Backup and restore guide.
- Administrator guide.
- User guides for key roles.
- Known limitations and future roadmap.

The final handover must distinguish clearly between:

- Fully implemented and tested features.
- Implemented features requiring user acceptance testing.
- Partially implemented features.
- Planned features not yet implemented.

**The overriding objective is to build a secure, integrated, auditable and extensible School CRM & ERP platform in which student records, academic operations, subject teacher assignments, results, cumulative transcripts, finance, alumni and the public website work together through consistent data and controlled workflows.**
