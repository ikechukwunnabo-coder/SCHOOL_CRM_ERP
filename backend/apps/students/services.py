from __future__ import annotations

from datetime import date

from django.db import IntegrityError, transaction

from apps.audit.services import log_event

from .models import Student, StudentGuardian, StudentLifecycleEvent

Status = Student.LifecycleStatus


class StudentWorkflowError(ValueError):
    pass


ALLOWED_TRANSITIONS = {
    Status.APPLICANT: {Status.ADMITTED, Status.WITHDRAWN},
    Status.ADMITTED: {Status.ENROLLED, Status.WITHDRAWN},
    Status.ENROLLED: {
        Status.ACTIVE,
        Status.PROMOTED,
        Status.REPEATED,
        Status.TRANSFERRED,
        Status.WITHDRAWN,
        Status.GRADUATED,
    },
    Status.ACTIVE: {
        Status.PROMOTED,
        Status.REPEATED,
        Status.TRANSFERRED,
        Status.WITHDRAWN,
        Status.GRADUATED,
    },
    Status.PROMOTED: {Status.ACTIVE, Status.WITHDRAWN, Status.TRANSFERRED},
    Status.REPEATED: {Status.ACTIVE, Status.WITHDRAWN},
    Status.TRANSFERRED: {Status.ACTIVE, Status.WITHDRAWN, Status.GRADUATED},
    Status.WITHDRAWN: {Status.ADMITTED},
    Status.GRADUATED: set(),
}


def change_lifecycle(
    actor,
    student: Student,
    target: Status,
    *,
    effective_date: date,
    reason="",
) -> Student:
    with transaction.atomic():
        locked = Student.objects.select_for_update().get(pk=student.pk)
        current = locked.status
        if target not in ALLOWED_TRANSITIONS.get(current, set()):
            raise StudentWorkflowError(f"invalid_transition:{current}->{target}")
        StudentLifecycleEvent.objects.create(
            student=locked,
            from_status=current,
            to_status=target,
            effective_date=effective_date,
            reason=reason,
            actor=actor,
        )
        locked.status = target
        locked.save(update_fields=["status", "updated_at"])
        student.refresh_from_db()
    log_event(
        "students.lifecycle_changed",
        actor=actor,
        target_type="students.Student",
        target_id=student.pk,
        institution_id=student.institution_id,
        campus_id=student.campus_id,
        reason=reason,
        change_summary={"from": current, "to": target},
        metadata={"effective_date": effective_date.isoformat()},
    )
    return student


def link_guardian(
    actor,
    student: Student,
    guardian,
    *,
    relationship: str,
    is_primary=False,
    financial_responsibility=False,
    authorized_pickup=False,
    portal_access=False,
) -> StudentGuardian:
    if guardian.institution_id != student.institution_id:
        raise StudentWorkflowError("guardian_cross_institution")
    try:
        with transaction.atomic():
            link = StudentGuardian.objects.create(
                student=student,
                guardian=guardian,
                relationship=relationship,
                is_primary=is_primary,
                financial_responsibility=financial_responsibility,
                authorized_pickup=authorized_pickup,
                portal_access=portal_access,
            )
    except IntegrityError as exc:
        raise StudentWorkflowError("guardian_already_linked") from exc
    log_event(
        "students.guardian_linked",
        actor=actor,
        target_type="students.StudentGuardian",
        target_id=link.pk,
        institution_id=student.institution_id,
        campus_id=student.campus_id,
        change_summary={"guardian_id": str(guardian.pk), "relationship": relationship},
    )
    return link
