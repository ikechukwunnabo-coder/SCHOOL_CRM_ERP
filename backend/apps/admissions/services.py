from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import log_event
from apps.core.identifiers import generate_identifier
from apps.students.models import Student

from .models import AdmissionDecision, Application, Enquiry

Status = Application.Status


class WorkflowError(ValueError):
    pass


class DuplicateIdentityError(WorkflowError):
    pass


ALLOWED_TRANSITIONS = {
    Status.STARTED: {Status.SUBMITTED, Status.WITHDRAWN},
    Status.SUBMITTED: {
        Status.UNDER_REVIEW,
        Status.REJECTED,
        Status.WITHDRAWN,
        Status.WAITLISTED,
        Status.DEFERRED,
    },
    Status.UNDER_REVIEW: {
        Status.ASSESSMENT,
        Status.APPROVED,
        Status.REJECTED,
        Status.WAITLISTED,
        Status.DEFERRED,
    },
    Status.ASSESSMENT: {
        Status.APPROVED,
        Status.REJECTED,
        Status.WAITLISTED,
        Status.DEFERRED,
    },
    Status.APPROVED: {Status.OFFERED, Status.WITHDRAWN},
    Status.OFFERED: {Status.ACCEPTED, Status.REJECTED, Status.WITHDRAWN},
    Status.ACCEPTED: {Status.ENROLLED, Status.WITHDRAWN},
    Status.ENROLLED: set(),
    Status.REJECTED: set(),
    Status.WITHDRAWN: set(),
    Status.WAITLISTED: set(),
    Status.DEFERRED: set(),
}

DECISION_TARGETS = {
    AdmissionDecision.Outcome.APPROVED: Status.APPROVED,
    AdmissionDecision.Outcome.REJECTED: Status.REJECTED,
    AdmissionDecision.Outcome.WAITLISTED: Status.WAITLISTED,
    AdmissionDecision.Outcome.DEFERRED: Status.DEFERRED,
}


def _audit(actor, action, application, *, reason="", change_summary=None, metadata=None):
    log_event(
        action,
        actor=actor,
        target_type="admissions.Application",
        target_id=application.pk,
        institution_id=application.institution_id,
        campus_id=application.campus_id,
        reason=reason,
        change_summary=change_summary or {},
        metadata=metadata or {},
    )


def _year_for(application: Application) -> int:
    cycle = str(application.cycle or "").strip()
    return int(cycle) if cycle.isdigit() else application.created_at.year


def create_enquiry(actor, **fields) -> Enquiry:
    with transaction.atomic():
        enquiry = Enquiry.objects.create(created_by=actor, **fields)
    log_event(
        "admissions.enquiry_created",
        actor=actor,
        target_type="admissions.Enquiry",
        target_id=enquiry.pk,
        institution_id=enquiry.institution_id,
        campus_id=enquiry.campus_id,
        change_summary={"full_name": enquiry.full_name},
    )
    return enquiry


def create_application(actor, **fields) -> Application:
    with transaction.atomic():
        institution = fields["institution"]
        cycle = str(fields.get("cycle") or timezone.now().year)
        application = Application.objects.create(
            created_by=actor,
            application_number=generate_identifier(
                institution,
                "application_number",
                year=_year_for_from_cycle(cycle),
                scope=cycle,
            ),
            **fields,
        )
    _audit(
        actor,
        "admissions.application_created",
        application,
        change_summary={"application_number": application.application_number},
    )
    return application


def _year_for_from_cycle(cycle: str) -> int:
    return int(cycle) if str(cycle).isdigit() else timezone.now().year


def change_status(actor, application: Application, target: Status, *, reason="") -> Application:
    with transaction.atomic():
        locked = Application.objects.select_for_update().get(pk=application.pk)
        current = locked.status
        if target not in ALLOWED_TRANSITIONS.get(current, set()):
            raise WorkflowError(f"invalid_transition:{current}->{target}")
        locked.status = target
        if target == Status.SUBMITTED and locked.submitted_at is None:
            locked.submitted_at = timezone.now()
        locked.save(update_fields=["status", "submitted_at", "updated_at"])
        application.refresh_from_db()
    _audit(
        actor,
        "admissions.status_changed",
        application,
        reason=reason,
        change_summary={"from": current, "to": target},
    )
    return application


def submit_application(actor, application: Application, *, reason="") -> Application:
    return change_status(actor, application, Status.SUBMITTED, reason=reason)


def review_application(actor, application: Application, *, reason="") -> Application:
    if application.status == Status.SUBMITTED:
        return change_status(actor, application, Status.UNDER_REVIEW, reason=reason)
    if application.status == Status.UNDER_REVIEW:
        return change_status(actor, application, Status.ASSESSMENT, reason=reason)
    raise WorkflowError(f"invalid_transition:{application.status}->review")


def record_decision(
    actor,
    application: Application,
    outcome: AdmissionDecision.Outcome,
    *,
    notes="",
) -> AdmissionDecision:
    with transaction.atomic():
        locked = Application.objects.select_for_update().get(pk=application.pk)
        if locked.status not in {
            Status.SUBMITTED,
            Status.UNDER_REVIEW,
            Status.ASSESSMENT,
        }:
            raise WorkflowError(f"decision_not_allowed:{locked.status}")
        if AdmissionDecision.objects.filter(application=locked).exists():
            raise WorkflowError("decision_already_recorded")
        decision = AdmissionDecision.objects.create(
            application=locked,
            outcome=outcome,
            decided_by=actor,
            notes=notes,
        )
        locked.status = DECISION_TARGETS[outcome]
        locked.save(update_fields=["status", "updated_at"])
        application.refresh_from_db()
    _audit(
        actor,
        "admissions.decision_recorded",
        application,
        reason=notes,
        change_summary={"outcome": outcome},
    )
    return decision


def offer_application(actor, application: Application, *, reason="") -> Application:
    return change_status(actor, application, Status.OFFERED, reason=reason)


def accept_application(actor, application: Application, *, reason="") -> Application:
    return change_status(actor, application, Status.ACCEPTED, reason=reason)


def _ensure_unique_identity(application: Application) -> None:
    duplicate = Student.objects.filter(
        institution_id=application.institution_id,
        first_name__iexact=application.first_name,
        last_name__iexact=application.last_name,
        date_of_birth=application.date_of_birth,
    ).exists()
    if duplicate:
        raise DuplicateIdentityError("duplicate_student_identity")


def enrol_application(
    actor,
    application: Application,
    *,
    guardian_links: list[dict] | None = None,
    reason="",
) -> Student:
    from apps.students.services import change_lifecycle, link_guardian

    with transaction.atomic():
        locked = Application.objects.select_for_update().get(pk=application.pk)
        if locked.status != Status.ACCEPTED:
            raise WorkflowError(f"enrolment_not_allowed:{locked.status}")
        if Student.objects.filter(source_application=locked).exists():
            raise WorkflowError("application_already_enrolled")
        _ensure_unique_identity(locked)

        try:
            with transaction.atomic():
                student = Student.objects.create(
                    institution_id=locked.institution_id,
                    campus_id=locked.campus_id,
                    source_application=locked,
                    admission_number=generate_identifier(
                        locked.institution,
                        "admission_number",
                        year=_year_for(locked),
                        scope=str(_year_for(locked)),
                    ),
                    first_name=locked.first_name,
                    last_name=locked.last_name,
                    date_of_birth=locked.date_of_birth,
                    gender=locked.gender,
                    admission_date=timezone.localdate(),
                    status=Student.LifecycleStatus.APPLICANT,
                )
        except IntegrityError as exc:
            raise DuplicateIdentityError("duplicate_student_identity") from exc

        change_lifecycle(
            actor,
            student,
            Student.LifecycleStatus.ADMITTED,
            effective_date=student.admission_date,
            reason=reason or "enrolment_from_application",
        )
        for link in guardian_links or []:
            guardian = link["guardian"]
            if guardian.institution_id != locked.institution_id:
                raise WorkflowError("guardian_cross_institution")
            link_guardian(
                actor,
                student,
                guardian,
                relationship=link["relationship"],
                is_primary=link.get("is_primary", False),
                financial_responsibility=link.get("financial_responsibility", False),
                authorized_pickup=link.get("authorized_pickup", False),
                portal_access=link.get("portal_access", False),
            )
        change_lifecycle(
            actor,
            student,
            Student.LifecycleStatus.ENROLLED,
            effective_date=student.admission_date,
            reason=reason or "enrolment_completed",
        )
        locked.status = Status.ENROLLED
        locked.save(update_fields=["status", "updated_at"])
        application.refresh_from_db()
    _audit(
        actor,
        "admissions.enrolment_completed",
        application,
        reason=reason,
        change_summary={
            "student_id": str(student.pk),
            "admission_number": student.admission_number,
        },
    )
    return student
