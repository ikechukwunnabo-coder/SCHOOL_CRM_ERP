# PHASE 0 — DISCOVERY, ARCHITECTURE AND IMPLEMENTATION READINESS

**Authoritative Reference:** `MASTER_CRM_ERP_SCHOOL_PROMPT.md`

## 1. Objective

Execute Phase 0 of the School CRM & ERP project before commencing broad application development.

The master specification is the authoritative source of requirements. Do not replace, simplify, silently omit or contradict its requirements.

Your responsibility is to translate the specification into a validated, implementation-ready technical blueprint.

## 2. Mandatory Deliverables

Prepare the following documents under the project's `docs/architecture/` directory:

1. `DECISIONS_REGISTER.md` — All confirmed decisions, outstanding questions, recommendations, owners and approval status.
2. `SYSTEM_ARCHITECTURE.md` — Overall architecture, application boundaries, component responsibilities and integration patterns.
3. `ENTITY_RELATIONSHIP_DIAGRAM.md` — Proposed database entities, relationships, constraints and ownership.
4. `DATA_DICTIONARY.md` — Important entities, fields, types, validation rules and relationships.
5. `RBAC_PERMISSION_MATRIX.md` — Roles, permissions, scope restrictions and approval responsibilities.
6. `WORKFLOW_SPECIFICATIONS.md` — Admissions, enrolment, attendance, examinations, results, transcripts, finance, procurement, inventory, asset management and ID-card workflows.
7. `API_DESIGN.md` — API conventions, authentication, authorization, pagination, filtering, validation and error handling.
8. `TECHNOLOGY_COMPATIBILITY_MATRIX.md` — Verified and pinned technology versions, compatibility evidence and package-management decisions.
9. `INTEGRATION_SPECIFICATIONS.md` — Payment, email, SMS, file storage and other external integration requirements.
10. `SECURITY_AND_PRIVACY_PLAN.md` — Threat considerations, privacy controls, audit requirements and data retention.
11. `TEST_STRATEGY.md` — Unit, integration, permission, workflow, frontend and end-to-end testing.
12. `DEPLOYMENT_AND_OPERATIONS_PLAN.md` — Environments, infrastructure assumptions, backups, monitoring, recovery and maintenance.
13. `IMPLEMENTATION_ROADMAP.md` — Dependencies, implementation sequence, milestones and release acceptance criteria.

## 3. Resolve Outstanding Decisions

Explicitly investigate and document:

- Compatible Python, Django, DRF, Node.js, React, TypeScript, PostgreSQL, Redis and Celery versions.
- Package managers and lockfile strategy.
- Authentication approach, including secure cookie authentication and CSRF protection.
- Payment gateway and communication provider selection criteria.
- File storage and backup strategy.
- Nigerian academic grading and school calendar configuration.
- Payroll and statutory calculation requirements.
- Legacy data migration requirements.
- Infrastructure sizing and performance targets.
- Backend application boundaries and dependency rules.

Do not invent provider credentials, statutory rates, school policies or unverified compatibility claims.

Where a decision requires management input, mark it **Pending Approval** and provide a recommended option with its implications.

## 4. Architecture Validation

Before approving the blueprint, verify:

- No duplicate ownership of core entities.
- No circular dependencies between Django applications.
- Institution and campus access restrictions are enforced server-side.
- Student and employee identities remain stable throughout their lifecycle.
- Historical academic results and grading schemes are preserved.
- Subject-teacher allocations have effective dates and audit history.
- Financial transactions have traceable posting, reversal and reconciliation rules.
- Inventory, procurement, asset management and finance have clearly defined boundaries.
- Student and staff ID cards are generated from existing biodata and support secure verification.
- Public CMS content is isolated from private ERP records.
- Sensitive operations have appropriate authorization and audit trails.

## 5. Implementation Discipline

Do not begin full-scale module development until:

1. Phase 0 deliverables are prepared.
2. Critical architectural conflicts are resolved.
3. Mandatory decisions are approved or explicitly documented as pending.
4. The database design and application boundaries are reviewed.
5. The implementation roadmap and MVP acceptance criteria are agreed.

You may create a minimal project scaffold if necessary to validate the proposed environment, but do not use that as justification to bypass Phase 0.

## 6. Final Phase 0 Report

Submit an executive and technical readiness report showing:

- Completed deliverables.
- Decisions confirmed.
- Decisions awaiting approval.
- Identified risks and dependencies.
- Architecture recommendations.
- Proposed implementation sequence.
- Outstanding blockers.
- A clear GO / CONDITIONAL GO / NO-GO recommendation for Release 1 development.

**Important:** Distinguish clearly between requirements that have been documented, decisions that have been approved, features that have actually been implemented, and features that have been tested. Never report planned work as completed work.