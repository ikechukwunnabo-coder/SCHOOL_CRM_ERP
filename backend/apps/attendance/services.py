from django.db import transaction
from django.utils import timezone

from apps.academics.models import ClassEnrolment
from apps.audit.services import log_event
from apps.employees.models import Employee
from apps.permissions.roles import (
    ADMIN_ROLES,
    HR_OFFICER,
    LEADERSHIP_ROLES,
    REGISTRAR,
    TEACHING_ROLES,
    role_matches,
)
from apps.permissions.services import (
    get_user_role_names,
    user_can_access_campus_id,
    user_can_access_institution,
)
from apps.teaching.services import resolve_teacher_scope

from .models import (
    AttendanceCorrection,
    AttendanceRecord,
    AttendanceSession,
    TeacherAttendanceRecord,
)


class AttendanceError(ValueError):
    pass


PRIVILEGED_ROLES = frozenset((*ADMIN_ROLES, *LEADERSHIP_ROLES, REGISTRAR))
TEACHER_ROLES = frozenset(TEACHING_ROLES)
APPROVER_ROLES = frozenset((*ADMIN_ROLES, *LEADERSHIP_ROLES, REGISTRAR, HR_OFFICER))
MARKER_ROLES = frozenset((*PRIVILEGED_ROLES, *TEACHER_ROLES, HR_OFFICER))


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


def _pk(value):
    return getattr(value, "pk", value)


def ensure_scope(user, institution_id, campus_id=None):
    if getattr(user, "is_superuser", False):
        return
    if not user_can_access_institution(user, _pk(institution_id)):
        raise AttendanceError("cross_institution_attendance")
    if not user_can_access_campus_id(user, _pk(campus_id)):
        raise AttendanceError("cross_campus_attendance")


def ensure_teacher_scope(user, offering):
    ensure_scope(user, offering.institution_id, offering.campus_id)
    if user.is_superuser:
        return
    roles = set(get_user_role_names(user))
    if roles & PRIVILEGED_ROLES:
        return
    if not roles & TEACHER_ROLES:
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
    ensure_scope(actor, record.institution_id, record.campus_id)
    if not reason.strip():
        raise AttendanceError("correction_reason_required")
    if new_status not in AttendanceRecord.Status.values:
        raise AttendanceError("invalid_attendance_status")
    if not (
        actor.is_superuser or role_matches(get_user_role_names(actor), PRIVILEGED_ROLES)
    ):
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


def mark_teacher_attendance(actor, *, employee, attendance_date, status):
    ensure_scope(actor, employee.institution_id, employee.campus_id)
    if not (
        actor.is_superuser or role_matches(get_user_role_names(actor), MARKER_ROLES)
    ):
        raise AttendanceError("teacher_attendance_mark_not_permitted")
    if status not in AttendanceRecord.Status.values:
        raise AttendanceError("invalid_attendance_status")
    with transaction.atomic():
        existing = (
            TeacherAttendanceRecord.objects.select_for_update()
            .filter(employee=employee, attendance_date=attendance_date)
            .first()
        )
        if existing and existing.approval_status == TeacherAttendanceRecord.ApprovalStatus.APPROVED:
            raise AttendanceError("approved_teacher_attendance_locked")
        record, _ = TeacherAttendanceRecord.objects.update_or_create(
            employee=employee,
            attendance_date=attendance_date,
            defaults={
                "institution_id": employee.institution_id,
                "campus_id": employee.campus_id,
                "status": status,
                "approval_status": TeacherAttendanceRecord.ApprovalStatus.DRAFT,
                "marked_by": actor,
                "approved_by": None,
                "approved_at": None,
            },
        )
    _audit(actor, "attendance.teacher_marked", record, change_summary={"status": status})
    return record


def ensure_teacher_attendance_editable(record):
    if record.approval_status == TeacherAttendanceRecord.ApprovalStatus.APPROVED:
        raise AttendanceError("approved_teacher_attendance_locked")


def approve_teacher_attendance(actor, record):
    ensure_scope(actor, record.institution_id, record.campus_id)
    if not (
        actor.is_superuser or role_matches(get_user_role_names(actor), APPROVER_ROLES)
    ):
        raise AttendanceError("teacher_attendance_approval_not_permitted")
    with transaction.atomic():
        locked = TeacherAttendanceRecord.objects.select_for_update().get(pk=record.pk)
        if locked.approval_status == TeacherAttendanceRecord.ApprovalStatus.APPROVED:
            raise AttendanceError("teacher_attendance_already_approved")
        locked.approval_status = TeacherAttendanceRecord.ApprovalStatus.APPROVED
        locked.approved_by = actor
        locked.approved_at = timezone.now()
        locked.save(
            update_fields=["approval_status", "approved_by", "approved_at", "updated_at"]
        )
    _audit(actor, "attendance.teacher_approved", locked)
    return locked


def query_teacher_attendance(user, *, employee=None, date_from=None, date_to=None, status=None):
    if employee is not None:
        ensure_scope(user, employee.institution_id, employee.campus_id)
    qs = TeacherAttendanceRecord.objects.all()
    if not user.is_superuser:
        qs = qs.filter(institution_id=user.institution_id)
        if user.campus_id:
            qs = qs.filter(campus_id=user.campus_id)
    if employee is not None:
        qs = qs.filter(employee_id=_pk(employee))
    if date_from is not None:
        qs = qs.filter(attendance_date__gte=date_from)
    if date_to is not None:
        qs = qs.filter(attendance_date__lte=date_to)
    if status is not None:
        qs = qs.filter(status=status)
    return qs.select_related("employee", "marked_by", "approved_by")


def scoped_employee(user, employee_id):
    qs = Employee.objects.all()
    if not user.is_superuser:
        qs = qs.filter(institution_id=user.institution_id)
        if user.campus_id:
            qs = qs.filter(campus_id=user.campus_id)
    return qs.filter(pk=employee_id).first()
