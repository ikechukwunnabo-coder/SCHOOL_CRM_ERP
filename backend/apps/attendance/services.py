from django.db import transaction

from apps.academics.models import ClassEnrolment
from apps.audit.services import log_event
from apps.permissions.services import get_user_role_names
from apps.teaching.services import resolve_teacher_scope

from .models import AttendanceCorrection, AttendanceRecord, AttendanceSession


class AttendanceError(ValueError):
    pass


PRIVILEGED_ROLES = {
    "Super Administrator",
    "Institution Administrator",
    "Registrar/Admissions",
    "Academic Head",
    "Principal",
}


def _audit(actor, action, obj, **kwargs):
    log_event(
        action,
        actor=actor,
        target_type=type(obj).__name__,
        target_id=obj.pk,
        institution_id=getattr(obj, "institution_id", None),
        campus_id=getattr(obj, "campus_id", None),
        **kwargs,
    )


def ensure_teacher_scope(user, offering):
    if user.is_superuser:
        return
    roles = set(get_user_role_names(user))
    if roles & PRIVILEGED_ROLES:
        return
    if "Teacher" not in roles:
        raise AttendanceError("missing_teacher_scope")
    assignments = resolve_teacher_scope(user)
    if not any(
        item.offering_id == offering.id
        and item.session_id == offering.session_id
        and (item.arm_id is None or item.arm_id == offering.arm_id)
        for item in assignments
    ):
        raise AttendanceError("teacher_not_assigned_to_offering")


def open_session(actor, *, offering, attendance_date):
    ensure_teacher_scope(actor, offering)
    if offering.session.is_closed:
        raise AttendanceError("closed_session")
    if not (offering.session.start_date <= attendance_date <= offering.session.end_date):
        raise AttendanceError("attendance_outside_session")
    if offering.term and not (
        offering.term.start_date <= attendance_date <= offering.term.end_date
    ):
        raise AttendanceError("attendance_outside_term")
    attendance = AttendanceSession.objects.create(
        institution_id=offering.institution_id,
        campus_id=offering.campus_id,
        session=offering.session,
        term=offering.term,
        class_level=offering.class_level,
        arm=offering.arm,
        offering=offering,
        attendance_date=attendance_date,
    )
    _audit(actor, "attendance.session_opened", attendance)
    return attendance


def expected_students(attendance):
    qs = ClassEnrolment.objects.filter(
        session=attendance.session,
        class_level=attendance.class_level,
        status=ClassEnrolment.Status.ACTIVE,
    )
    if attendance.arm_id:
        qs = qs.filter(arm=attendance.arm)
    return [item.student for item in qs.select_related("student")]


def mark_attendance(actor, *, attendance, student, status):
    ensure_teacher_scope(actor, attendance.offering)
    if attendance.status != AttendanceSession.Status.OPEN:
        raise AttendanceError("attendance_session_closed")
    if status not in AttendanceRecord.Status.values:
        raise AttendanceError("invalid_attendance_status")
    if student.institution_id != attendance.institution_id:
        raise AttendanceError("cross_institution_attendance")
    with transaction.atomic():
        locked = AttendanceSession.objects.select_for_update().get(pk=attendance.pk)
        if locked.status != AttendanceSession.Status.OPEN:
            raise AttendanceError("attendance_session_closed")
        record, _ = AttendanceRecord.objects.update_or_create(
            attendance_session=locked,
            student=student,
            defaults={"status": status, "marked_by": actor},
        )
    _audit(actor, "attendance.marked", record, change_summary={"status": status})
    return record


def close_session(actor, attendance):
    ensure_teacher_scope(actor, attendance.offering)
    with transaction.atomic():
        locked = AttendanceSession.objects.select_for_update().get(pk=attendance.pk)
        locked.status = AttendanceSession.Status.CLOSED
        locked.closed_by = actor
        locked.save(update_fields=["status", "closed_by", "updated_at"])
    _audit(actor, "attendance.session_closed", locked)
    return locked


def correct_attendance(actor, *, record, new_status, reason):
    if not reason.strip():
        raise AttendanceError("correction_reason_required")
    if new_status not in AttendanceRecord.Status.values:
        raise AttendanceError("invalid_attendance_status")
    if actor.is_superuser or set(get_user_role_names(actor)) & PRIVILEGED_ROLES:
        pass
    else:
        raise AttendanceError("correction_not_permitted")
    with transaction.atomic():
        locked = AttendanceRecord.objects.select_for_update().get(pk=record.pk)
        correction = AttendanceCorrection.objects.create(
            record=locked,
            previous_status=locked.status,
            new_status=new_status,
            reason=reason,
            requested_by=actor,
            approved_by=actor,
        )
        locked.status = new_status
        locked.correction_count += 1
        locked.save(update_fields=["status", "correction_count", "updated_at"])
    _audit(
        actor,
        "attendance.corrected",
        correction,
        change_summary={"from": correction.previous_status, "to": correction.new_status},
    )
    return correction
