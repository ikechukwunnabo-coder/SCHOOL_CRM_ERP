# MASTER DEVELOPMENT PROMPT
# INTEGRATED SCHOOL CRM & ERP MANAGEMENT SYSTEM

## 1. PROJECT OVERVIEW

Act as a Senior Software Architect, Enterprise ERP Developer, Database Architect, Full-Stack Engineer, UI/UX Designer, Cybersecurity Specialist, and Quality Assurance Engineer.

Your task is to design and develop a comprehensive, enterprise-grade School Customer Relationship Management (CRM) and Enterprise Resource Planning (ERP) Management System.

The platform must integrate all major school operations into one centralized application, covering:

- Student Relationship Management (CRM).
- Admissions and Enrolment.
- Student Information Management.
- Academic Management.
- Subject and Teacher Management.
- Examination and Assessment Management.
- Student Transcript Management.
- Attendance Management.
- School Fees and Financial Management.
- Accounting and Budget Management.
- Human Resource Management.
- Payroll Management.
- Learning Management System (LMS).
- Parent and Guardian Portal.
- Teacher Portal.
- Student Portal.
- Alumni Management.
- Library Management.
- Inventory and Procurement.
- Transport Management.
- Hostel and Boarding Management.
- Communication and Notifications.
- School Website and Content Management System (CMS).
- Executive Dashboards and Business Intelligence.

The platform should initially support Nursery, Primary, and Secondary schools, with an extensible architecture that can accommodate other educational institutions in the future.

The application must be fully functional, integrated, secure, scalable, responsive, and production-ready.

Do not build a collection of disconnected applications. Develop one integrated institutional management ecosystem with interconnected modules and centralized data management.

---

# 2. TECHNOLOGY STACK AND PROJECT STRUCTURE

Use the following technology stack consistently.

### Backend
- Python.
- Django 5.2 LTS.
- Django REST Framework.
- PostgreSQL.
- Celery for background tasks.
- Redis for caching and background task processing.
- JWT authentication with secure session management.
- OpenAPI documentation using drf-spectacular.

### Frontend
- React.
- TypeScript.
- Vite.
- Tailwind CSS.
- shadcn/ui.
- Recharts for analytics and visualizations.
- React Hook Form.
- Zod for validation.
- TanStack Query for server-state management.

### Infrastructure
- Docker and Docker Compose.
- Nginx.
- Gunicorn.
- PostgreSQL backups.
- Environment-based configuration.
- S3-compatible storage for production file management.

### Project directory

Create the project using this structure:

```text
school_erp/
│
├── school_erp_venv/
│
├── backend/
│   ├── config/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── schools/
│   │   ├── campuses/
│   │   ├── students/
│   │   ├── parents/
│   │   ├── admissions/
│   │   ├── alumni/
│   │   ├── academics/
│   │   ├── subjects/
│   │   ├── teachers/
│   │   ├── examinations/
│   │   ├── transcripts/
│   │   ├── attendance/
│   │   ├── finance/
│   │   ├── accounting/
│   │   ├── hr/
│   │   ├── payroll/
│   │   ├── lms/
│   │   ├── library/
│   │   ├── inventory/
│   │   ├── procurement/
│   │   ├── transport/
│   │   ├── hostel/
│   │   ├── communication/
│   │   ├── cms/
│   │   ├── maintenance/
│   │   ├── helpdesk/
│   │   ├── reports/
│   │   └── audit/
│   ├── media/
│   ├── static/
│   └── requirements/
│
├── frontend/
│   ├── public/
│   └── src/
│       ├── app/
│       ├── assets/
│       ├── components/
│       ├── features/
│       ├── hooks/
│       ├── layouts/
│       ├── services/
│       ├── contexts/
│       ├── routes/
│       ├── types/
│       └── utils/
│
├── docker/
├── docs/
├── scripts/
├── backups/
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

The virtual environment must be created inside the root project directory as `school_erp_venv`.

Maintain strict separation between backend and frontend.

Use modular monolithic architecture. Keep Django applications logically separated while allowing secure integration through centralized APIs.

---

# 3. STUDENT RELATIONSHIP MANAGEMENT (CRM)

Develop a comprehensive Student Information Management System.

### Student registration and profiles

- Student registration.
- Unique student identification number.
- Student photographs.
- Full biodata.
- Date of birth.
- Gender.
- Residential address.
- Contact information.
- Nationality.
- State and local government information.
- Parent and guardian information.
- Emergency contacts.
- Previous school records.
- Medical information with restricted access.
- Supporting document uploads.
- Admission history.
- Academic history.
- Financial history.
- Attendance history.
- Disciplinary records.
- Awards and achievements.

### Student lifecycle management

Manage the complete student lifecycle:

1. Enquiry.
2. Application.
3. Admission.
4. Registration.
5. Enrolment.
6. Class allocation.
7. Academic progression.
8. Class promotion.
9. Graduation.
10. Withdrawal or transfer.
11. Alumni transition.

Provide historical records of student movements between classes, arms, campuses, academic sessions, and schools.

Never overwrite historical academic records when a student is promoted.

---

# 4. ADMISSIONS AND ENROLMENT MANAGEMENT

Implement a complete admission workflow.

Features:

- Online admission applications.
- Admission enquiries.
- Applicant database.
- Application document uploads.
- Application verification.
- Entrance examinations.
- Interview scheduling.
- Admission approval and rejection.
- Waiting list.
- Admission letters.
- Offer acceptance.
- Admission fee invoicing.
- Admission payment tracking.
- Automatic student profile creation after admission approval.
- Admission statistics.
- Enquiry follow-up management.

The public website must provide an online admission application form connected to the backend.

---

# 5. ACADEMIC MANAGEMENT SYSTEM

Develop a comprehensive academic administration module.

### Academic configuration

- Academic sessions.
- Terms and semesters.
- School calendar.
- Classes.
- Class arms and sections.
- Departments.
- Subjects.
- Academic levels.
- Curriculum.
- Grading systems.
- Assessment structures.
- Promotion rules.

All academic structures and grading rules must be configurable.

### Class management

- Class creation.
- Class allocation.
- Class teacher assignment.
- Student enrolment into classes.
- Student transfers between arms.
- Class lists.
- Class performance monitoring.
- Class attendance.
- Class timetables.

### Curriculum and lesson management

- Curriculum management.
- Scheme of work.
- Lesson plans.
- Lesson notes.
- Teaching schedules.
- Learning objectives.
- Teaching resources.
- Lesson completion tracking.

---

# 6. SUBJECT AND TEACHER MANAGEMENT

This is a critical component of the platform.

Develop a dedicated Subject and Teacher Allocation Management System.

### Subject management

Administrators must be able to:

- Create subjects.
- Edit subject information.
- Assign subject codes.
- Categorize subjects.
- Define compulsory subjects.
- Define elective subjects.
- Associate subjects with academic levels.
- Assign subjects to specific classes.
- Configure subject credit units where applicable.
- Configure subject assessment structures.
- Configure subject-specific grading rules where required.

### Subject teacher allocation

The system must support assigning teachers to individual subjects across different classes and arms.

For example:

| Class | Subject | Assigned Subject Teacher |
|---|---|---|
| JSS 1A | Mathematics | Teacher A |
| JSS 1A | English | Teacher B |
| JSS 1A | Basic Science | Teacher C |
| JSS 1B | Mathematics | Teacher A |
| JSS 1B | English | Teacher D |
| SS 1A | Mathematics | Teacher E |

The above is an illustrative allocation. Actual assignments must be configurable.

### Required functionality

- Assign one or multiple teachers to a subject where appropriate.
- Assign a teacher to multiple subjects.
- Assign a teacher to multiple classes.
- Assign different teachers to the same subject across different class arms.
- Set primary and assistant subject teachers where required.
- Define allocation by academic session and term.
- Prevent conflicting assignments where applicable.
- Maintain teacher-subject allocation history.
- Support bulk subject allocation.
- Support bulk teacher allocation.
- View teacher workload.
- View subject coverage.
- Generate subject-teacher allocation reports.

### Teacher dashboard

Each teacher must have access to a dedicated dashboard displaying:

- Assigned classes.
- Assigned subjects.
- Assigned students.
- Teaching timetable.
- Attendance responsibilities.
- Lesson plans.
- Assessment records.
- Examination schedules.
- Result-entry responsibilities.
- Assignment management.
- Academic performance reports.

### Result-entry permissions

Teachers should only be allowed to enter and manage results for subjects and classes assigned to them, subject to authorized administrative overrides.

The system must maintain a complete history of result submissions, modifications, and approvals.

---

# 7. EXAMINATION AND ASSESSMENT MANAGEMENT

Develop a comprehensive examination management module.

### Assessment configuration

- Continuous assessment.
- Class tests.
- Assignments.
- Practical assessments.
- Midterm examinations.
- Terminal examinations.
- End-of-session examinations.
- Custom assessment components.

Administrators must be able to configure assessment weightings.

For example:

- First CA: 10%.
- Second CA: 10%.
- Examination: 80%.

The system must validate that configured assessment components total the required percentage.

### Examination management

- Examination creation.
- Examination timetable.
- Examination subjects.
- Student examination registration.
- Examination attendance.
- Result entry.
- Bulk result upload.
- Result validation.
- Result submission.
- Result approval.
- Result publication.
- Result correction workflow.
- Broadsheet generation.

### Subject teacher result submission workflow

1. Subject teacher logs in.
2. Teacher views assigned subjects and classes.
3. Teacher selects the academic session and term.
4. Teacher selects the class and subject.
5. Teacher enters assessment scores.
6. System validates scores against configured maximum values.
7. Teacher saves results.
8. Teacher submits results for approval.
9. Authorized academic administrator reviews results.
10. Approved results become available for report generation and publication.

Teachers must not be able to alter approved results without authorization and a recorded correction workflow.

### Result processing

Automatically calculate:

- Continuous assessment totals.
- Examination scores.
- Subject totals.
- Grades.
- Grade points where applicable.
- Class averages.
- Student averages.
- Cumulative averages.
- Subject positions.
- Overall positions where configured.
- Performance classifications.

All calculations must use configurable academic rules rather than hardcoded assumptions.

---

# 8. STUDENT REPORT CARD AND TRANSCRIPT MANAGEMENT

This module is mandatory and must be fully implemented.

Develop a dedicated Student Academic Records and Transcript Management System.

### A. Termly report cards

Generate professional student report cards containing:

- School name and logo.
- Student photograph.
- Student identification number.
- Student full name.
- Class and arm.
- Academic session.
- Term.
- Subjects offered.
- Continuous assessment scores.
- Examination scores.
- Total scores.
- Grades.
- Subject remarks.
- Subject teacher comments.
- Class teacher comments.
- Principal's comments.
- Attendance statistics.
- Class performance.
- Overall average.
- Promotion status.
- Conduct and behavioural assessment.
- Skills and extracurricular assessments.
- Authorized signatures.

Provide PDF download, printing, and secure parent portal access.

### B. Cumulative academic records

Maintain a permanent academic history for every student.

Records must be organized by:

- Academic session.
- Term or semester.
- Class or grade level.
- Subject.
- Assessment.
- Final score.
- Grade.
- Credit units where applicable.
- Academic remarks.

A student's academic history must remain accessible even after promotion, graduation, withdrawal, or transfer.

### C. Student transcript generation

The system must be capable of generating complete student academic transcripts across multiple academic sessions and classes.

A transcript must not be limited to the current term or current class.

It must retrieve the student's approved historical academic results from the database.

### Transcript information

Each transcript must contain:

1. School name and official branding.
2. School address and contact details.
3. Transcript identification number.
4. Student full name.
5. Student admission number.
6. Date of birth where authorized.
7. Student photograph where configured.
8. Programme or educational level.
9. Date of admission.
10. Academic sessions attended.
11. Classes or grade levels completed.
12. Subjects taken in each academic period.
13. Scores obtained in each subject.
14. Grades awarded.
15. Grade-point values where applicable.
16. Credit units where applicable.
17. Termly or semester averages.
18. Annual academic performance.
19. Cumulative performance.
20. Promotion history.
21. Graduation status.
22. Date of transcript issuance.
23. Authorized signatures.
24. Official school stamp or verification mark.

### D. Transcript formats

Support:

- Complete academic transcript.
- Term-specific transcript.
- Session-specific transcript.
- Cumulative transcript.
- Graduation transcript.
- Transfer transcript.
- Official transcript.
- Unofficial student academic statement.

### E. Transcript generation workflow

1. Authorized user searches for a student.
2. User selects the required transcript type.
3. System retrieves all relevant approved academic records.
4. System validates academic completeness.
5. System calculates required cumulative values using the applicable grading rules.
6. System generates the transcript.
7. Authorized personnel review and approve official transcripts.
8. System assigns a unique transcript reference number.
9. Approved transcript is generated as a professionally formatted PDF.
10. Transcript issuance is recorded in the audit log.

### F. Transcript verification

Implement a secure transcript verification mechanism.

- Unique transcript reference.
- QR code or verification code.
- Secure verification page.
- Issuance date.
- Verification status.
- Issuing authority.
- Transcript history.

External institutions must be able to verify an issued transcript without accessing the student's private school records.

### G. Transcript integrity

- Never invent missing academic results.
- Do not treat unpublished or unapproved results as official results.
- Preserve historical grading scales.
- Preserve academic records after graduation.
- Record every official transcript issuance.
- Maintain version history for corrected transcripts.
- Restrict transcript generation and access to authorized personnel.
- Provide a clear indication when an academic record is incomplete.

The transcript module must be fully integrated with student management, subject allocation, examination management, result processing, and alumni management.

---

# 9. STUDENT ATTENDANCE MANAGEMENT

Features:

- Daily attendance.
- Class attendance.
- Subject-period attendance where configured.
- Teacher attendance.
- Staff attendance.
- Late arrival.
- Early departure.
- Absence reasons.
- Attendance summaries.
- Parent notifications.
- Attendance reports.
- Attendance analytics.
- Optional biometric integration.
- Optional QR-code attendance.

---

# 10. SCHOOL FEES AND FINANCIAL ERP

Develop an integrated financial management system.

### School fees

- Tuition fees.
- Registration fees.
- Examination fees.
- Development levies.
- Transportation fees.
- Boarding fees.
- Uniform fees.
- Other configurable charges.
- Class-based fee structures.
- Student-specific charges.
- Discounts.
- Scholarships.
- Bursaries.
- Installment plans.
- Outstanding balances.

### Invoicing and payments

- Automatic invoice generation.
- Payment allocation.
- Partial payments.
- Payment receipts.
- Payment history.
- Refunds.
- Payment reconciliation.
- Cash payments.
- Bank transfers.
- POS payments.
- Online payments.
- Parent payment portal.
- Automated payment reminders.

### Accounting

Implement proper double-entry accounting.

- Chart of accounts.
- General ledger.
- Accounts receivable.
- Accounts payable.
- Journal entries.
- Cashbook.
- Bank reconciliation.
- Trial balance.
- Profit and loss.
- Balance sheet.
- Cash flow statement.
- Budget management.
- Financial reporting.

Financial transactions must have appropriate approval, validation, and audit workflows.

---

# 11. HUMAN RESOURCE MANAGEMENT AND PAYROLL

Features:

- Employee registration.
- Staff profiles.
- Recruitment.
- Onboarding.
- Departments.
- Job titles.
- Qualifications.
- Employment history.
- Employment contracts.
- Leave management.
- Staff attendance.
- Performance appraisal.
- Training records.
- Disciplinary records.
- Salary structures.
- Allowances.
- Deductions.
- Payroll processing.
- Payslip generation.
- Payroll reports.
- Employee exit management.

---

# 12. LEARNING MANAGEMENT SYSTEM (LMS)

Features:

- Digital classroom.
- Learning materials.
- Digital resources.
- Lesson uploads.
- Assignments.
- Assignment submissions.
- Online quizzes.
- Question banks.
- Online assessments.
- Video lesson integration.
- Student progress tracking.
- Teacher feedback.
- Discussion forums.
- Learning reports.

---

# 13. PARENT AND GUARDIAN PORTAL

Provide a dedicated parent portal.

Parents should be able to:

- View their children's profiles.
- View multiple children under one account.
- Monitor attendance.
- View examination results.
- Download report cards.
- Request official transcripts where permitted.
- View assignments.
- View school announcements.
- Receive notifications.
- View invoices.
- Make school fee payments.
- Download receipts.
- Communicate with teachers.
- Submit enquiries and complaints.
- Apply for student leave.
- View school calendar.
- View transport information.

Parents must only access records of children explicitly linked to their accounts and authorized for access.

---

# 14. TEACHER PORTAL

Provide a dedicated teacher portal with:

- Teacher dashboard.
- Personal profile.
- Assigned subjects.
- Assigned classes and arms.
- Subject allocation history.
- Student lists.
- Teaching timetable.
- Attendance management.
- Lesson planning.
- Scheme of work.
- Assessment entry.
- Examination result entry.
- Result submission.
- Assignment management.
- Student performance analysis.
- Parent communication.
- Leave applications.

The teacher portal must automatically display the teacher's active assignments based on authorized academic allocations.

---

# 15. STUDENT PORTAL

Provide a dedicated student portal.

Features:

- Personal profile.
- Academic history.
- Current class.
- Subjects.
- Timetable.
- Attendance.
- Examination results.
- Report cards.
- Academic progress.
- Assignments.
- Learning materials.
- Online examinations.
- School announcements.
- Fee information where authorized.
- Transcript request functionality where permitted.

---

# 16. ALUMNI MANAGEMENT SYSTEM

Retain and fully implement Alumni Management as a dedicated module.

The system must automatically support transitioning graduated students into the alumni database.

### Alumni registration and records

- Alumni identification number.
- Student admission number.
- Full name.
- Photograph.
- Graduation year.
- Graduation class.
- Academic history.
- Contact information.
- Email address.
- Phone number.
- Residential address.
- Current occupation.
- Employer or organization.
- Professional qualifications.
- Further education.
- Achievements and awards.
- Alumni membership status.

### Alumni management features

- Automatic alumni profile creation after graduation.
- Alumni directory.
- Graduation-year grouping.
- Class reunion management.
- Alumni events.
- Alumni communication.
- Alumni announcements.
- Alumni newsletters.
- Alumni networking.
- Alumni membership management.
- Alumni donations and fundraising.
- Alumni contribution records.
- Alumni engagement reports.
- Alumni employment and career tracking.
- Alumni feedback and surveys.

### Alumni portal

Provide a dedicated alumni portal where former students can:

- Register and update their profiles.
- Update employment information.
- Update contact details.
- View alumni announcements.
- Participate in alumni events.
- Connect with other alumni.
- Receive school newsletters.
- Contribute to school development.
- Request academic transcripts.
- Request verification of academic records.

Alumni academic records must remain permanently linked to their original student records.

Graduation must not result in the deletion or loss of historical academic data.

---

# 17. LIBRARY MANAGEMENT

Features:

- Book catalogue.
- Book categories.
- ISBN management.
- Book inventory.
- Borrowing.
- Returns.
- Due dates.
- Overdue notifications.
- Lost and damaged books.
- Library fines.
- Borrowing history.
- Library reports.

---

# 18. INVENTORY AND PROCUREMENT MANAGEMENT

Features:

- Inventory catalogue.
- Stock categories.
- Stock levels.
- Stock issuance.
- Stock transfers.
- Stock adjustments.
- Supplier records.
- Purchase requisitions.
- Purchase orders.
- Goods received notes.
- Procurement approval.
- Asset register.
- Asset allocation.
- Maintenance records.
- Inventory valuation.
- Low-stock alerts.

---

# 19. TRANSPORT MANAGEMENT

Features:

- Vehicle registration.
- Vehicle documentation.
- Driver records.
- Transport routes.
- Bus stops.
- Student route allocation.
- Transport fee management.
- Fuel records.
- Vehicle maintenance.
- Trip schedules.
- Transport attendance.
- Parent notifications.
- Optional GPS integration.

---

# 20. HOSTEL AND BOARDING MANAGEMENT

Features:

- Hostel registration.
- Dormitory management.
- Room allocation.
- Bed allocation.
- Boarding student records.
- Hostel attendance.
- Hostel fees.
- Visitor records.
- Maintenance requests.
- Hostel reports.

---

# 21. COMMUNICATION AND NOTIFICATION MANAGEMENT

Support:

- Internal messaging.
- Email.
- SMS.
- WhatsApp Business API integration.
- Parent notifications.
- Teacher notifications.
- Student notifications.
- Payment reminders.
- Attendance alerts.
- Examination notifications.
- Admission notifications.
- Emergency announcements.
- Notification templates.
- Delivery logs.

Communication providers must be configurable.

---

# 22. SCHOOL WEBSITE AND CONTENT MANAGEMENT SYSTEM (CMS)

Develop a public-facing school website fully integrated with the CRM and ERP.

### Public website pages

- Home.
- About Us.
- School History.
- Mission and Vision.
- Management and Leadership.
- Academics.
- Nursery.
- Primary.
- Secondary.
- Admissions.
- Online Admission Application.
- School Facilities.
- Gallery.
- News and Events.
- Academic Calendar.
- Staff and Teachers.
- Alumni.
- Contact Us.
- FAQs.
- Careers.
- Parent Portal Login.
- Student Portal Login.
- Staff Portal Login.
- Alumni Portal Login.

### CMS management

Authorized administrators must be able to manage:

- Website pages.
- School logo.
- Favicon.
- Homepage banners.
- Gallery.
- News.
- Events.
- Navigation menus.
- Footer content.
- Contact information.
- Social media links.
- Admission forms.
- SEO metadata.
- Website colours and themes.
- Draft and published content.
- Scheduled publishing.
- Media library.

No direct source-code modification should be required for routine website content updates.

---

# 23. USER MANAGEMENT AND ROLE-BASED ACCESS CONTROL

Implement configurable Role-Based Access Control (RBAC).

Include:

- Super Administrator.
- Proprietor / Director.
- School Administrator.
- Principal.
- Vice Principal.
- Registrar.
- Bursar.
- Accountant.
- HR Manager.
- Teacher.
- Subject Teacher.
- Class Teacher.
- Parent / Guardian.
- Student.
- Alumni.
- Librarian.
- Inventory Officer.
- Transport Manager.
- Hostel Manager.
- Receptionist.
- IT Administrator.
- Auditor.

Support permissions at module, action, campus, department, and record levels.

Permissions must include:

- View.
- Create.
- Edit.
- Delete.
- Approve.
- Reject.
- Publish.
- Export.
- Print.

Backend authorization must always be authoritative.

---

# 24. EXECUTIVE DASHBOARD AND BUSINESS INTELLIGENCE

Develop a comprehensive management dashboard.

Display:

- Total enrolment.
- New admissions.
- Student population by class.
- Student attendance.
- Staff attendance.
- Fees collected.
- Outstanding fees.
- Revenue.
- Expenditure.
- Financial performance.
- Academic performance.
- Class performance.
- Subject performance.
- Teacher workload.
- Examination trends.
- Graduation statistics.
- Alumni population.
- Inventory statistics.
- Transport statistics.
- Admission conversion rates.

Provide interactive charts, filters, reports, and drill-down capabilities.

Support filtering by:

- Academic session.
- Term.
- Campus.
- Department.
- Class.
- Subject.
- Teacher.
- Date range.

---

# 25. SCHOOL CONFIGURATION AND CUSTOMIZATION

The system must allow authorized administrators to configure:

- School name.
- School logo.
- School favicon.
- School address.
- School contact details.
- School colours.
- School branding.
- Academic sessions.
- Terms and semesters.
- Classes.
- Arms.
- Subjects.
- Grading systems.
- Assessment structures.
- Promotion rules.
- Fee categories.
- Fee structures.
- Departments.
- Staff roles.
- User permissions.
- Report templates.
- Notification settings.
- School policies.
- Campus configurations.

Avoid hardcoding school-specific information.

Support multiple campuses under one institution, with the architectural capacity for future independent school tenants.

---

# 26. REPORTS AND DOCUMENT GENERATION

Generate professional institutional documents, including:

- Admission letters.
- Student biodata.
- Student ID cards.
- Class lists.
- Student attendance reports.
- Examination broadsheets.
- Termly report cards.
- Cumulative academic records.
- Official student transcripts.
- Unofficial academic statements.
- Graduation certificates.
- Transfer documents.
- Payment invoices.
- Payment receipts.
- Financial statements.
- Staff ID cards.
- Payslips.
- Payroll reports.
- Purchase orders.
- Inventory reports.
- Library reports.
- Alumni reports.
- Management reports.

Support PDF, Excel, CSV, and print formats where appropriate.

All documents must support school branding, appropriate authorization, and access control.

---

# 27. UI/UX DESIGN REQUIREMENTS

Create a premium, modern, professional enterprise application.

Use:

- Clean layouts.
- Consistent typography.
- Professional colour system.
- Responsive dashboards.
- Collapsible sidebar.
- Top navigation.
- Breadcrumb navigation.
- Global search.
- Notification centre.
- User profile menu.
- Professional data tables.
- Advanced filtering.
- Reusable forms.
- Modal dialogs.
- Confirmation dialogs.
- Toast notifications.
- Loading states.
- Empty states.
- Error states.
- Light and dark themes.

Ensure that the administrative dashboard, teacher portal, student portal, parent portal, alumni portal, and public website have appropriate interfaces.

Do not produce generic, repetitive AI-generated dashboards.

Use a consistent and reusable design system.

Prioritize usability, accessibility, performance, and professional presentation.

---

# 28. SECURITY AND DATA PROTECTION

Implement:

- Secure authentication.
- Strong password hashing.
- Password reset.
- Optional multi-factor authentication.
- Session management.
- Role-based authorization.
- API permissions.
- CSRF protection.
- XSS protection.
- SQL injection protection.
- Rate limiting.
- Secure file uploads.
- Audit logging.
- Login history.
- Failed login tracking.
- Database backup.
- Database restoration.
- Sensitive data access restrictions.
- Data encryption where appropriate.
- Data retention policies.
- Privacy and consent management.

Maintain audit trails for:

- Student record changes.
- Teacher allocations.
- Examination result changes.
- Result approvals.
- Transcript generation.
- Transcript corrections.
- Financial transactions.
- Fee adjustments.
- Payroll processing.
- User permission changes.
- Administrative activities.

Never expose confidential student, parent, financial, or academic records to unauthorized users.

---

# 29. DEVELOPMENT PHASES

Implement the project incrementally.

### Phase 1: Foundation
- Project setup.
- Virtual environment.
- Django configuration.
- React configuration.
- PostgreSQL.
- Authentication.
- RBAC.
- School configuration.
- Campus configuration.
- UI design system.

### Phase 2: Student CRM and Admissions
- Student profiles.
- Parent records.
- Admissions.
- Enquiries.
- Enrolment.

### Phase 3: Academic and Teacher Management
- Academic sessions.
- Classes and arms.
- Departments.
- Subjects.
- Teacher records.
- Subject-teacher allocation.
- Timetables.
- Curriculum.
- Lesson management.

### Phase 4: Attendance and Examination
- Attendance.
- Continuous assessment.
- Examination management.
- Subject result entry.
- Result submission.
- Result approval.
- Result computation.
- Report cards.
- Broadsheets.

### Phase 5: Transcript and Alumni
- Historical academic records.
- Transcript generation.
- Transcript approval.
- Transcript verification.
- Graduation management.
- Alumni database.
- Alumni portal.
- Alumni events and communication.

### Phase 6: Finance and Accounting
- Fee structures.
- Invoices.
- Payments.
- Receipts.
- Accounting.
- Budgeting.
- Financial reporting.

### Phase 7: HR and Payroll
- Employee management.
- Leave.
- Staff attendance.
- Payroll.
- Payslips.

### Phase 8: Operational ERP
- Inventory.
- Procurement.
- Library.
- Transport.
- Hostel.
- Maintenance.

### Phase 9: Learning and Stakeholder Portals
- LMS.
- Parent portal.
- Teacher portal.
- Student portal.

### Phase 10: Public Website and CMS
- Public website.
- Website CMS.
- Online admission.
- School branding.
- SEO.

### Phase 11: Analytics and Automation
- Executive dashboard.
- Reports.
- Notifications.
- AI-assisted analytics.

### Phase 12: Testing and Production Deployment
- Functional testing.
- Integration testing.
- Security testing.
- Performance testing.
- Backup and recovery.
- Docker deployment.
- Nginx configuration.
- Production documentation.

---

# 30. MANDATORY DEVELOPMENT RULES

Follow these instructions throughout the entire development process.

1. Analyze the requirements and project directory before implementation.
2. Create a comprehensive architecture and development plan.
3. Establish the database schema before implementing dependent modules.
4. Use modular Django applications.
5. Use React and TypeScript for the frontend.
6. Implement real backend APIs for all functional features.
7. Never use static mock data as a substitute for working functionality.
8. Never create frontend-only features that are not backed by functional APIs.
9. Maintain proper relationships between all modules.
10. Avoid duplicate database records.
11. Use configurable business rules.
12. Enforce permissions at the backend level.
13. Maintain comprehensive audit logs.
14. Write automated tests for critical functionality.
15. Test all module integrations.
16. Implement proper error handling.
17. Maintain API documentation.
18. Maintain README.md.
19. Maintain .env.example.
20. Never expose passwords, API keys, or secrets.
21. Use database migrations properly.
22. Optimize database queries.
23. Ensure responsive frontend design.
24. Do not leave non-functional buttons or placeholder pages.
25. Do not claim a feature is complete without testing it.
26. Preserve historical academic and financial records.
27. Never allow unauthorized changes to approved examination results.
28. Never generate official transcripts from unapproved or incomplete academic records.
29. Maintain historical teacher-subject allocation records.
30. Ensure that graduated students transition into alumni records without losing their original student information.

---

# 31. ACCEPTANCE CRITERIA

The project will only be considered complete when the following workflows have been implemented and successfully tested.

### Student admission workflow
An applicant submits an online application, the registrar processes the application, the administrator approves admission, and the system creates the student's profile.

### Subject teacher workflow
An administrator creates subjects, registers teachers, assigns teachers to subjects and classes, and teachers can access only their assigned academic responsibilities.

### Examination workflow
A subject teacher enters scores, submits results, an authorized administrator approves them, and the system generates accurate student results.

### Transcript workflow
An authorized administrator selects a graduated student, retrieves all approved historical academic records, generates a complete cumulative transcript, approves it, and produces a verifiable PDF document.

### Alumni workflow
A student graduates, the system preserves the original student profile and academic history, and creates or activates the corresponding alumni record and portal access.

### Finance workflow
The bursar configures fees, generates invoices, records payments, issues receipts, and views outstanding balances.

### Parent workflow
A parent logs in, views linked children, monitors attendance, accesses approved results, views fees, and downloads receipts.

### Teacher workflow
A teacher logs in, views assigned classes and subjects, records attendance, enters assessments, and submits results.

### Public website workflow
An administrator creates and publishes website content through the CMS, and the public website displays the approved content.

All workflows must be supported by actual database records, working APIs, frontend functionality, and automated tests.

---

# 32. FINAL INSTRUCTION TO THE AI DEVELOPMENT AGENT

Begin by inspecting the existing project directory.

If no project exists, create the complete project structure and establish the development environment.

Before writing application code:

1. Produce the technical architecture.
2. Produce the database relationship design.
3. Define module dependencies.
4. Define authentication and permission architecture.
5. Produce the development roadmap.
6. Identify major risks and integration requirements.

Then begin implementation with Phase 1.

Do not attempt to generate the entire system in one uncontrolled coding operation.

Complete each phase systematically, test it, fix errors, document it, and proceed to the next phase.

Maintain a development progress document identifying:

- Completed modules.
- Modules in progress.
- Outstanding functionality.
- Known issues.
- Test results.
- Integration status.
- Next implementation tasks.

The ultimate objective is to deliver a fully integrated, secure, maintainable, professional, and production-ready School CRM & ERP platform.

**The system must function as a complete school operating platform, not merely a student registration application.** Subject-teacher allocation, examination management, cumulative transcript generation, and alumni management are core requirements and must not be treated as optional or deferred features.
