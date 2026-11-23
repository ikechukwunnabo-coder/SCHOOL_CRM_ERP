from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.academics.tests.m3_helpers import (
    client_for,
    make_employee,
    make_school,
    make_structure,
    make_user,
)
from apps.permissions.roles import SUBJECT_TEACHER

from .. import services as teaching_services
from ..models import TeacherAssignment, TeacherWorkloadPolicy, Timetable, TimetableSlot


@pytest.mark.django_db
def test_workload_policy_selection_and_bootstrap(monkeypatch):
    institution, campuses = make_school("workloadpolicy", ("main", "annex"))
    TeacherWorkloadPolicy.objects.create(
        institution=institution,
        effective_from=date(2026, 1, 1),
        max_hours=20,
    )
    TeacherWorkloadPolicy.objects.create(
        institution=institution,
        campus=campuses[0],
        effective_from=date(2026, 6, 1),
        max_hours=30,
    )
    TeacherWorkloadPolicy.objects.create(
        institution=institution,
        campus=campuses[1],
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 6, 30),
        max_hours=50,
    )

    assert (
        teaching_services.resolve_workload_policy(
            institution=institution, campus=campuses[0], on_date=date(2026, 7, 1)
        ).max_hours
        == 30
    )
    assert (
        teaching_services.resolve_workload_policy(
            institution=institution, campus=campuses[1], on_date=date(2026, 7, 1)
        ).max_hours
        == 20
    )
    assert (
        teaching_services.resolve_workload_policy(
            institution=institution, campus=campuses[0], on_date=date(2026, 3, 1)
        ).max_hours
        == 20
    )

    fallback_institution, fallback_campuses = make_school("workloaddefault")
    monkeypatch.setattr(teaching_services, "DEFAULT_WORKLOAD_MAX_HOURS", 18)
    fallback = teaching_services.resolve_workload_policy(
        institution=fallback_institution,
        campus=fallback_campuses[0],
        on_date=date(2026, 7, 1),
    )
    assert fallback._state.adding
    assert not TeacherWorkloadPolicy.objects.filter(institution=fallback_institution).exists()
    assert fallback.max_hours == 18
    bootstrapped = teaching_services.bootstrap_default_workload_policy(
        institution=fallback_institution,
        campus=fallback_campuses[0],
        effective_from=date(2026, 7, 1),
    )
    assert bootstrapped.pk is not None
    assert bootstrapped.max_hours == 18


@pytest.mark.django_db
def test_reassignment_does_not_double_count_closed_assignment():
    institution, campuses = make_school("reassign")
    admin = make_user("reassign-admin", institution, campuses[0])
    employee = make_employee(institution, campuses[0], "REASSIGN-1")
    structure = make_structure(admin, institution, campuses[0], "reassign")
    TeacherWorkloadPolicy.objects.create(
        institution=institution,
        effective_from=timezone.localdate() - timedelta(days=30),
        max_hours=40,
    )
    today = timezone.localdate()
    original = teaching_services.assign_teacher(
        admin,
        offering=structure["offering"],
        employee=employee,
        role=TeacherAssignment.Role.LEAD,
        start_date=today - timedelta(days=1),
        end_date=today + timedelta(days=30),
        workload_hours=35,
    )
    replacement = teaching_services.assign_teacher(
        admin,
        offering=structure["offering"],
        employee=employee,
        role=TeacherAssignment.Role.LEAD,
        start_date=today,
        end_date=today + timedelta(days=30),
        workload_hours=35,
        reassign=True,
    )
    original.refresh_from_db()
    assert original.status == TeacherAssignment.Status.CLOSED
    assert replacement.status == TeacherAssignment.Status.ACTIVE
    assert teaching_services.workload_hours(employee) == 35

    policy = TeacherWorkloadPolicy.objects.get(institution=institution)
    policy.max_hours = 30
    policy.save(update_fields=["max_hours"])
    with pytest.raises(teaching_services.TeachingError, match="workload_exceeded"):
        teaching_services.assign_teacher(
            admin,
            offering=structure["offering"],
            employee=employee,
            role=TeacherAssignment.Role.LEAD,
            start_date=today,
            end_date=today + timedelta(days=30),
            workload_hours=35,
            reassign=True,
        )
    replacement.refresh_from_db()
    assert replacement.status == TeacherAssignment.Status.ACTIVE


@pytest.mark.django_db
def test_timetable_recurrence_approval_publication_and_revision():
    institution, campuses = make_school("timetablepolicy")
    admin = make_user("timetablepolicy-admin", institution, campuses[0])
    employee = make_employee(institution, campuses[0], "TIMETABLE-1")
    structure = make_structure(admin, institution, campuses[0], "timetablepolicy")
    timetable = teaching_services.create_timetable(
        admin,
        session=structure["session"],
        class_level=structure["level"],
        arm=structure["arm"],
        name="Term 1",
    )
    slot = teaching_services.add_slot(
        admin,
        timetable=timetable,
        day_of_week=1,
        period=1,
        offering=structure["offering"],
        employee=employee,
        room="Room A",
        recurrence=TimetableSlot.Recurrence.WEEKLY,
        recurrence_interval=2,
        recurrence_until=date(2026, 12, 1),
    )
    assert slot.recurrence == TimetableSlot.Recurrence.WEEKLY
    assert slot.recurrence_interval == 2
    assert slot.recurrence_until == date(2026, 12, 1)

    with pytest.raises(teaching_services.TeachingError, match="timetable_not_approved"):
        teaching_services.publish_timetable(admin, timetable)
    teaching_services.approve_timetable(admin, timetable)
    published = teaching_services.publish_timetable(admin, timetable)
    assert published.status == Timetable.Status.PUBLISHED
    assert published.published_by_id == admin.id

    client = client_for(admin)
    assert client.patch(
        f"/api/v1/timetables/{timetable.id}/", {"name": "Changed"}, format="json"
    ).status_code == 409
    assert client.post(
        f"/api/v1/timetables/{timetable.id}/add-slot/",
        {
            "day_of_week": 2,
            "period": 2,
            "offering": str(structure["offering"].id),
            "employee": str(employee.id),
            "room": "Room B",
        },
        format="json",
    ).status_code == 409

    revision = teaching_services.create_timetable_revision(admin, timetable)
    assert revision.version == 2
    assert revision.status == Timetable.Status.DRAFT
    assert revision.revision_of_id == timetable.id
    assert revision.slots.count() == 1
    assert client.patch(
        f"/api/v1/timetables/{revision.id}/", {"name": "Revised"}, format="json"
    ).status_code == 200


@pytest.mark.django_db
def test_teaching_querysets_hide_cross_scope_objects():
    inst_a, campuses_a = make_school("teachscopea", ("main", "annex"))
    inst_b, campuses_b = make_school("teachscopeb", ("main",))
    admin_a = make_user("teachscopea-admin", inst_a, campuses_a[0])
    admin_annex = make_user("teachscopea-annex-admin", inst_a, campuses_a[1])
    admin_b = make_user("teachscopeb-admin", inst_b, campuses_b[0])
    campus_user = make_user(
        "teachscopea-campus", inst_a, campuses_a[0], role="Campus Administrator"
    )
    employee_a = make_employee(inst_a, campuses_a[0], "TEACH-A-1")
    employee_annex = make_employee(inst_a, campuses_a[1], "TEACH-A-2")
    employee_b = make_employee(inst_b, campuses_b[0], "TEACH-B-1")
    struct_a = make_structure(admin_a, inst_a, campuses_a[0], "teach-a")
    struct_annex = make_structure(admin_annex, inst_a, campuses_a[1], "teach-annex")
    struct_b = make_structure(admin_b, inst_b, campuses_b[0], "teach-b")

    def build(actor, employee, structure):
        assignment = teaching_services.assign_teacher(
            actor,
            offering=structure["offering"],
            employee=employee,
            role=TeacherAssignment.Role.LEAD,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            workload_hours=1,
        )
        timetable = teaching_services.create_timetable(
            actor,
            session=structure["session"],
            class_level=structure["level"],
            arm=structure["arm"],
            name="Scope timetable",
        )
        slot = teaching_services.add_slot(
            actor,
            timetable=timetable,
            day_of_week=1,
            period=1,
            offering=structure["offering"],
            employee=employee,
            room="Scope room",
        )
        return assignment, timetable, slot

    own = build(admin_a, employee_a, struct_a)
    annex = build(admin_annex, employee_annex, struct_annex)
    other = build(admin_b, employee_b, struct_b)
    policy_a = TeacherWorkloadPolicy.objects.create(
        institution=inst_a,
        campus=campuses_a[0],
        effective_from=date(2026, 1, 1),
        max_hours=10,
    )
    policy_annex = TeacherWorkloadPolicy.objects.create(
        institution=inst_a,
        campus=campuses_a[1],
        effective_from=date(2026, 1, 1),
        max_hours=10,
    )
    policy_b = TeacherWorkloadPolicy.objects.create(
        institution=inst_b,
        campus=campuses_b[0],
        effective_from=date(2026, 1, 1),
        max_hours=10,
    )

    cases = (
        ("teacher-assignments", own[0], annex[0], other[0]),
        ("timetables", own[1], annex[1], other[1]),
        ("timetable-slots", own[2], annex[2], other[2]),
        ("workload-policies", policy_a, policy_annex, policy_b),
    )
    client = client_for(admin_a)
    for path, own_obj, annex_obj, other_obj in cases:
        listing = client.get(f"/api/v1/{path}/")
        assert listing.status_code == 200, listing.data
        visible = {item["id"] for item in listing.data["results"]}
        assert str(own_obj.id) in visible
        assert str(other_obj.id) not in visible
        assert client.get(f"/api/v1/{path}/{other_obj.id}/").status_code == 404
        assert client.patch(f"/api/v1/{path}/{other_obj.id}/", {}, format="json").status_code == 404

        campus_client = client_for(campus_user)
        annex_url = f"/api/v1/{path}/{annex_obj.id}/"
        assert campus_client.get(annex_url).status_code == 404
        assert campus_client.patch(annex_url, {}, format="json").status_code == 404

    assert client.post(
        f"/api/v1/timetables/{own[1].id}/add-slot/",
        {
            "day_of_week": 2,
            "period": 2,
            "offering": str(struct_b["offering"].id),
            "employee": str(employee_a.id),
            "room": "Cross room",
        },
        format="json",
    ).status_code == 404

    teacher = make_user("teachscopea-teacher", inst_a, campuses_a[0], role=SUBJECT_TEACHER)
    teacher_client = client_for(teacher)
    assert teacher_client.get("/api/v1/teacher-assignments/").status_code == 200
    assert teacher_client.post(
        "/api/v1/workload-policies/",
        {
            "institution": str(inst_a.id),
            "effective_from": "2026-01-01",
            "max_hours": 20,
        },
        format="json",
    ).status_code == 403
