from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Max, Q, Sum
from django.utils import timezone

from apps.audit.services import log_event
from apps.employees.models import Employee
from apps.permissions.roles import (
    ADMIN_ROLES,
    HOD,
    PRINCIPAL,
    VICE_PRINCIPAL,
    role_matches,
)
from apps.permissions.services import (
    get_user_role_names,
    user_can_access_campus_id,
    user_can_access_institution,
)

from .models import (
    TeacherAssignment,
    TeacherWorkloadPolicy,
    Timetable,
    TimetableSlot,
)

DEFAULT_WORKLOAD_MAX_HOURS = getattr(
    settings, "TEACHING_DEFAULT_WORKLOAD_MAX_HOURS", 40
)
APPROVER_ROLES = frozenset((*ADMIN_ROLES, HOD, PRINCIPAL, VICE_PRINCIPAL))


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


def _pk(value):
    return getattr(value, "pk", value)


def ensure_scope(user, institution_id, campus_id=None):
    if getattr(user, "is_superuser", False):
        return
    if not user_can_access_institution(user, _pk(institution_id)):
        raise TeachingError("cross_institution_access")
    if not user_can_access_campus_id(user, _pk(campus_id)):
        raise TeachingError("cross_campus_access")


def resolve_workload_policy(
    *, institution=None, institution_id=None, campus=None, campus_id=None, on_date=None
):
    institution_id = _pk(institution if institution is not None else institution_id)
    campus_id = _pk(campus if campus is not None else campus_id)
    effective_on = on_date or timezone.localdate()
    qs = TeacherWorkloadPolicy.objects.filter(
        institution_id=institution_id,
        effective_from__lte=effective_on,
    ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=effective_on))
    if campus_id is not None:
        campus_policy = qs.filter(campus_id=campus_id).order_by("-effective_from").first()
        if campus_policy:
            return campus_policy
    institution_policy = qs.filter(campus_id__isnull=True).order_by("-effective_from").first()
    if institution_policy:
        return institution_policy
    return TeacherWorkloadPolicy(
        institution_id=institution_id,
        campus_id=campus_id,
        effective_from=effective_on,
        max_hours=DEFAULT_WORKLOAD_MAX_HOURS,
    )


def bootstrap_default_workload_policy(
    *, institution, campus=None, effective_from=None, name="Default workload"
):
    effective_from = effective_from or timezone.localdate()
    existing = resolve_workload_policy(
        institution=institution, campus=campus, on_date=effective_from
    )
    if not existing._state.adding:
        return existing
    policy = TeacherWorkloadPolicy.objects.create(
        institution=institution,
        campus=campus,
        name=name,
        effective_from=effective_from,
        max_hours=DEFAULT_WORKLOAD_MAX_HOURS,
    )
    _audit(None, "teaching.workload_policy_bootstrapped", policy)
    return policy


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


def workload_hours(employee):
    return (
        TeacherAssignment.objects.filter(
            employee=employee,
            status=TeacherAssignment.Status.ACTIVE,
        ).aggregate(total=Sum("workload_hours"))["total"]
        or 0
    )


def close_assignment(actor, assignment, *, end_date=None):
    if assignment.status == TeacherAssignment.Status.CLOSED:
        return assignment
    end_date = end_date or timezone.localdate() - timedelta(days=1)
    with transaction.atomic():
        locked = TeacherAssignment.objects.select_for_update().get(pk=assignment.pk)
        if locked.status == TeacherAssignment.Status.CLOSED:
            return locked
        locked.status = TeacherAssignment.Status.CLOSED
        locked.end_date = end_date
        locked.save(update_fields=["status", "end_date", "updated_at"])
    _audit(actor, "teaching.assignment_closed", locked)
    return locked


def assign_teacher(
    actor, *, offering, employee, role, start_date, end_date, workload_hours=0, reassign=False
):
    if employee.status != Employee.Status.ACTIVE:
        raise TeachingError("inactive_employee")
    if end_date < start_date:
        raise TeachingError("invalid_assignment_dates")
    ensure_scope(actor, offering.institution_id, offering.campus_id)
    ensure_scope(actor, employee.institution_id, employee.campus_id)
    if employee.institution_id != offering.institution_id:
        raise TeachingError("cross_institution_assignment")
    if offering.campus_id and employee.campus_id and offering.campus_id != employee.campus_id:
        raise TeachingError("cross_campus_assignment")
    if offering.session.is_closed:
        raise TeachingError("closed_session")
    policy = resolve_workload_policy(
        institution_id=offering.institution_id,
        campus_id=offering.campus_id,
        on_date=start_date,
    )
    with transaction.atomic():
        previous = TeacherAssignment.objects.filter(
            offering=offering,
            role=role,
            status=TeacherAssignment.Status.ACTIVE,
        ).first()
        if previous and not reassign:
            raise TeachingError("assignment_exists")
        if previous:
            close_assignment(actor, previous, end_date=start_date - timedelta(days=1))
        active = TeacherAssignment.objects.filter(
            employee=employee,
            status=TeacherAssignment.Status.ACTIVE,
        )
        if previous:
            active = active.exclude(pk=previous.pk)
        current_workload = active.aggregate(total=Sum("workload_hours"))["total"] or 0
        if current_workload + workload_hours > policy.max_hours:
            raise TeachingError("workload_exceeded")
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
    ensure_scope(actor, session.institution_id, session.campus_id)
    timetable = Timetable.objects.create(
        session=session, class_level=class_level, arm=arm, name=name, version=version
    )
    _audit(actor, "teaching.timetable_created", timetable)
    return timetable


def ensure_timetable_editable(timetable):
    if timetable.status == Timetable.Status.PUBLISHED:
        raise TeachingError("published_timetable_requires_new_revision")


def ensure_slot_editable(slot):
    ensure_timetable_editable(slot.timetable)


def validate_recurrence(*, recurrence, interval=1, until=None):
    if recurrence not in TimetableSlot.Recurrence.values:
        raise TeachingError("invalid_recurrence")
    if not interval or interval < 1:
        raise TeachingError("invalid_recurrence_interval")


def update_timetable(actor, timetable, *, name=None, arm=None):
    ensure_scope(actor, timetable.institution_id, timetable.campus_id)
    ensure_timetable_editable(timetable)
    if name is not None:
        timetable.name = name
    if arm is not None:
        timetable.arm = arm
    timetable.save(update_fields=["name", "arm", "updated_at"])
    _audit(actor, "teaching.timetable_updated", timetable)
    return timetable


def create_timetable_revision(actor, timetable):
    ensure_scope(actor, timetable.institution_id, timetable.campus_id)
    version = (
        Timetable.objects.filter(
            session_id=timetable.session_id,
            class_level_id=timetable.class_level_id,
            arm_id=timetable.arm_id,
        ).aggregate(latest=Max("version"))["latest"]
        or 0
    ) + 1
    revision = Timetable.objects.create(
        session=timetable.session,
        class_level=timetable.class_level,
        arm=timetable.arm,
        revision_of=timetable,
        name=timetable.name,
        version=version,
        status=Timetable.Status.DRAFT,
    )
    for slot in timetable.slots.all():
        TimetableSlot.objects.create(
            timetable=revision,
            day_of_week=slot.day_of_week,
            period=slot.period,
            offering=slot.offering,
            employee=slot.employee,
            room=slot.room,
            recurrence=slot.recurrence,
            recurrence_interval=slot.recurrence_interval,
            recurrence_until=slot.recurrence_until,
        )
    _audit(
        actor,
        "teaching.timetable_revision_created",
        revision,
        change_summary={"version": version},
    )
    return revision


def _check_approval_role(actor):
    if getattr(actor, "is_superuser", False):
        return
    if not role_matches(get_user_role_names(actor), APPROVER_ROLES):
        raise TeachingError("timetable_approval_not_permitted")


def approve_timetable(actor, timetable):
    ensure_scope(actor, timetable.institution_id, timetable.campus_id)
    ensure_timetable_editable(timetable)
    _check_approval_role(actor)
    if timetable.approved_at:
        raise TeachingError("timetable_already_approved")
    timetable.approved_by = actor
    timetable.approved_at = timezone.now()
    timetable.save(update_fields=["approved_by", "approved_at", "updated_at"])
    _audit(actor, "teaching.timetable_approved", timetable)
    return timetable


def publish_timetable(actor, timetable):
    ensure_scope(actor, timetable.institution_id, timetable.campus_id)
    ensure_timetable_editable(timetable)
    _check_approval_role(actor)
    if not timetable.approved_at:
        raise TeachingError("timetable_not_approved")
    timestamp = timezone.now()
    timetable.status = Timetable.Status.PUBLISHED
    timetable.published_by = actor
    timetable.published_at = timestamp
    timetable.save(
        update_fields=["status", "published_by", "published_at", "updated_at"]
    )
    _audit(actor, "teaching.timetable_published", timetable)
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


def add_slot(
    actor,
    *,
    timetable,
    day_of_week,
    period,
    offering,
    employee,
    room,
    recurrence=TimetableSlot.Recurrence.WEEKLY,
    recurrence_interval=1,
    recurrence_until=None,
):
    validate_recurrence(
        recurrence=recurrence, interval=recurrence_interval, until=recurrence_until
    )
    with transaction.atomic():
        locked = Timetable.objects.select_for_update().get(pk=timetable.pk)
        ensure_scope(actor, locked.institution_id, locked.campus_id)
        ensure_timetable_editable(locked)
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
            recurrence=recurrence,
            recurrence_interval=recurrence_interval,
            recurrence_until=recurrence_until,
        )
    _audit(actor, "teaching.slot_created", slot)
    return slot


def update_slot(actor, slot, **changes):
    ensure_scope(actor, slot.institution_id, slot.campus_id)
    ensure_slot_editable(slot)
    allowed = {
        "day_of_week",
        "period",
        "offering",
        "employee",
        "room",
        "recurrence",
        "recurrence_interval",
        "recurrence_until",
    }
    unknown = set(changes) - allowed
    if unknown:
        raise TeachingError("invalid_slot_update")
    validate_recurrence(
        recurrence=changes.get("recurrence", slot.recurrence),
        interval=changes.get("recurrence_interval", slot.recurrence_interval),
        until=changes.get("recurrence_until", slot.recurrence_until),
    )
    for field, value in changes.items():
        setattr(slot, field, value)
    slot.save(update_fields=[*changes.keys(), "updated_at"])
    _audit(actor, "teaching.slot_updated", slot)
    return slot
