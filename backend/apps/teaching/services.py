from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.audit.services import log_event
from apps.employees.models import Employee

from .models import TeacherAssignment, Timetable, TimetableSlot


class TeachingError(ValueError):
    pass


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


def resolve_teacher_scope(user):
    employee = Employee.objects.filter(user=user, status=Employee.Status.ACTIVE).first()
    if not employee:
        return []
    today = timezone.localdate()
    return list(
        TeacherAssignment.objects.filter(
            employee=employee,
            status=TeacherAssignment.Status.ACTIVE,
            start_date__lte=today,
            end_date__gte=today,
        ).select_related("offering", "class_level", "arm", "session", "term")
    )


def assign_teacher(
    actor, *, offering, employee, role, start_date, end_date, workload_hours=0, reassign=False
):
    if employee.status != Employee.Status.ACTIVE:
        raise TeachingError("inactive_employee")
    if end_date < start_date:
        raise TeachingError("invalid_assignment_dates")
    if employee.institution_id != offering.institution_id:
        raise TeachingError("cross_institution_assignment")
    if offering.session.is_closed:
        raise TeachingError("closed_session")
    with transaction.atomic():
        current_workload = (
            TeacherAssignment.objects.filter(
                employee=employee,
                status=TeacherAssignment.Status.ACTIVE,
            ).aggregate(total=Sum("workload_hours"))["total"]
            or 0
        )
        if current_workload + workload_hours > 40:
            raise TeachingError("workload_exceeded")
        previous = TeacherAssignment.objects.filter(
            offering=offering,
            role=role,
            status=TeacherAssignment.Status.ACTIVE,
        ).first()
        if previous and not reassign:
            raise TeachingError("assignment_exists")
        if previous and reassign:
            previous.status = TeacherAssignment.Status.CLOSED
            previous.end_date = start_date - timezone.timedelta(days=1)
            previous.save(update_fields=["status", "end_date", "updated_at"])
            _audit(actor, "teaching.assignment_closed", previous)
        assignment = TeacherAssignment.objects.create(
            institution_id=offering.institution_id,
            campus_id=offering.campus_id,
            session=offering.session,
            term=offering.term,
            class_level=offering.class_level,
            arm=offering.arm,
            offering=offering,
            employee=employee,
            role=role,
            start_date=start_date,
            end_date=end_date,
            workload_hours=workload_hours,
            authorized_by=actor,
        )
    _audit(actor, "teaching.assignment_created", assignment, change_summary={"role": role})
    return assignment


def create_timetable(actor, *, session, class_level, arm=None, name, version=1):
    timetable = Timetable.objects.create(
        session=session, class_level=class_level, arm=arm, name=name, version=version
    )
    _audit(actor, "teaching.timetable_created", timetable)
    return timetable


def check_slot_conflicts(*, timetable, day_of_week, period, employee, room, offering):
    qs = TimetableSlot.objects.filter(
        timetable__session_id=timetable.session_id,
        day_of_week=day_of_week,
        period=period,
    )
    if qs.filter(employee=employee).exists():
        raise TeachingError("teacher_double_booked")
    if qs.filter(
        timetable__class_level_id=timetable.class_level_id, timetable__arm_id=timetable.arm_id
    ).exists():
        raise TeachingError("class_double_booked")
    if room and qs.filter(room__iexact=room).exists():
        raise TeachingError("room_double_booked")
    if offering.session_id != timetable.session_id:
        raise TeachingError("offering_session_mismatch")


def add_slot(actor, *, timetable, day_of_week, period, offering, employee, room):
    with transaction.atomic():
        locked = Timetable.objects.select_for_update().get(pk=timetable.pk)
        check_slot_conflicts(
            timetable=locked,
            day_of_week=day_of_week,
            period=period,
            employee=employee,
            room=room,
            offering=offering,
        )
        slot = TimetableSlot.objects.create(
            timetable=locked,
            day_of_week=day_of_week,
            period=period,
            offering=offering,
            employee=employee,
            room=room,
        )
    _audit(actor, "teaching.slot_created", slot)
    return slot
