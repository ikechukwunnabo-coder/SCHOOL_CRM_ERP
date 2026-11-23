from datetime import date

import pytest
from django.utils import timezone

from apps.academics.tests.m3_helpers import (
    client_for,
    make_employee,
    make_school,
    make_structure,
    make_user,
)
from apps.permissions.roles import EXAM_OFFICER, HOD, SUBJECT_TEACHER
from apps.teaching import services as teaching_services
from apps.teaching.models import TeacherAssignment

from .. import services as attendance_services
from ..models import AttendanceRecord, TeacherAttendanceRecord


@pytest.mark.django_db
def test_student_attendance_scope_and_action_idor():
    inst_a, campuses_a = make_school("attscopea", ("main", "annex"))
    inst_b, campuses_b = make_school("attscopeb", ("main",))
    admin_a = make_user("attscopea-admin", inst_a, campuses_a[0])
    admin_annex = make_user("attscopea-annex-admin", inst_a, campuses_a[1])
    admin_b = make_user("attscopeb-admin", inst_b, campuses_b[0])
    campus_user = make_user(
        "attscopea-campus", inst_a, campuses_a[0], role="Campus Administrator"
    )
    officer = make_user("attscopea-officer", inst_a, campuses_a[0], role=EXAM_OFFICER)
    hod = make_user("attscopea-hod", inst_a, campuses_a[0], role=HOD)

    struct_a = make_structure(admin_a, inst_a, campuses_a[0], "att-a", student=True)
    struct_annex = make_structure(
        admin_annex, inst_a, campuses_a[1], "att-annex", student=True
    )
    struct_b = make_structure(admin_b, inst_b, campuses_b[0], "att-b", student=True)

    def build(actor, structure):
        session = attendance_services.open_session(
            actor, offering=structure["offering"], attendance_date=date(2026, 11, 23)
        )
        record = attendance_services.mark_attendance(
            actor,
            attendance=session,
            student=structure["enrolment"].student,
            status=AttendanceRecord.Status.PRESENT,
        )
        correction = attendance_services.correct_attendance(
            actor, record=record, new_status="absent", reason="verified register error"
        )
        return session, record, correction

    own = build(admin_a, struct_a)
    annex = build(admin_annex, struct_annex)
    other = build(admin_b, struct_b)

    cases = (
        ("attendance-sessions", own[0], annex[0], other[0]),
        ("attendance-records", own[1], annex[1], other[1]),
        ("attendance-corrections", own[2], annex[2], other[2]),
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
        "/api/v1/attendance-sessions/open/",
        {"offering": str(struct_b["offering"].id), "attendance_date": "2026-11-23"},
        format="json",
    ).status_code == 404
    assert client.post(
        f"/api/v1/attendance-sessions/{own[0].id}/mark/",
        {"student": str(struct_b["enrolment"].student.id), "status": "present"},
        format="json",
    ).status_code == 404

    officer_client = client_for(officer)
    assert officer_client.get("/api/v1/attendance-sessions/").status_code == 403
    assert officer_client.post(
        "/api/v1/attendance-sessions/open/",
        {"offering": str(struct_a["offering"].id), "attendance_date": "2026-11-24"},
        format="json",
    ).status_code == 403
    assert client_for(hod).get("/api/v1/attendance-sessions/").status_code == 200


@pytest.mark.django_db
def test_teacher_attendance_mark_approve_query_and_workflow():
    institution, campuses = make_school("teacheratt", ("main", "annex"))
    teacher_user = make_user("teacheratt-teacher", institution, campuses[0], role=SUBJECT_TEACHER)
    teacher = make_employee(institution, campuses[0], "TEACHERATT-1", user=teacher_user)
    hod = make_user("teacheratt-hod", institution, campuses[0], role=HOD)
    admin_annex = make_user("teacheratt-annex-admin", institution, campuses[1])
    other_institution, other_campuses = make_school("teacherattother")
    other_employee = make_employee(other_institution, other_campuses[0], "TEACHERATT-OTHER")

    teacher_client = client_for(teacher_user)
    hod_client = client_for(hod)
    mark_response = teacher_client.post(
        "/api/v1/teacher-attendance/mark/",
        {
            "employee": str(teacher.id),
            "attendance_date": "2026-11-23",
            "status": "present",
        },
        format="json",
    )
    assert mark_response.status_code == 201, mark_response.data
    record_id = mark_response.data["id"]
    assert mark_response.data["approval_status"] == TeacherAttendanceRecord.ApprovalStatus.DRAFT

    approve_response = hod_client.post(f"/api/v1/teacher-attendance/{record_id}/approve/")
    assert approve_response.status_code == 200, approve_response.data
    assert (
        approve_response.data["approval_status"]
        == TeacherAttendanceRecord.ApprovalStatus.APPROVED
    )
    assert str(approve_response.data["approved_by"]) == str(hod.id)

    assert teacher_client.patch(
        f"/api/v1/teacher-attendance/{record_id}/", {"status": "absent"}, format="json"
    ).status_code == 409
    assert teacher_client.post(
        "/api/v1/teacher-attendance/mark/",
        {
            "employee": str(teacher.id),
            "attendance_date": "2026-11-23",
            "status": "absent",
        },
        format="json",
    ).status_code == 409

    query = teacher_client.get(
        "/api/v1/teacher-attendance/query/",
        {
            "employee": str(teacher.id),
            "date_from": "2026-11-01",
            "date_to": "2026-11-30",
            "status": "present",
        },
    )
    assert query.status_code == 200, query.data
    assert [item["id"] for item in query.data] == [record_id]
    assert teacher_client.get(
        "/api/v1/teacher-attendance/query/", {"employee": str(other_employee.id)}
    ).status_code == 404
    assert teacher_client.post(
        "/api/v1/teacher-attendance/mark/",
        {
            "employee": str(other_employee.id),
            "attendance_date": "2026-11-23",
            "status": "present",
        },
        format="json",
    ).status_code == 404

    annex_record = attendance_services.mark_teacher_attendance(
        admin_annex,
        employee=make_employee(institution, campuses[1], "TEACHERATT-2"),
        attendance_date=timezone.localdate(),
        status="present",
    )
    assert hod_client.post(
        f"/api/v1/teacher-attendance/{annex_record.id}/approve/"
    ).status_code == 404
    assert teacher_client.get(
        f"/api/v1/teacher-attendance/{annex_record.id}/"
    ).status_code == 404


@pytest.mark.django_db
def test_teacher_attendance_service_roles_and_scope():
    institution, campuses = make_school("teacherattroles")
    admin = make_user("teacherattroles-admin", institution, campuses[0])
    teacher_user = make_user(
        "teacherattroles-teacher", institution, campuses[0], role=SUBJECT_TEACHER
    )
    employee = make_employee(institution, campuses[0], "TEACHERATTROLES-1")
    record = attendance_services.mark_teacher_attendance(
        admin, employee=employee, attendance_date=date(2026, 11, 23), status="present"
    )
    with pytest.raises(
        attendance_services.AttendanceError, match="teacher_attendance_approval_not_permitted"
    ):
        attendance_services.approve_teacher_attendance(teacher_user, record)

    other_institution, other_campuses = make_school("teacherattrolesother")
    other_admin = make_user("teacherattrolesother-admin", other_institution, other_campuses[0])
    other_employee = make_employee(
        other_institution, other_campuses[0], "TEACHERATTROLES-OTHER"
    )
    with pytest.raises(attendance_services.AttendanceError, match="cross_institution_attendance"):
        attendance_services.mark_teacher_attendance(
            other_admin, employee=employee, attendance_date=date(2026, 11, 23), status="present"
        )
    assert other_employee.institution_id == other_institution.id


@pytest.mark.django_db
def test_attendance_teacher_scope_uses_canonical_roles():
    institution, campuses = make_school("canonscope")
    admin = make_user("canonscope-admin", institution, campuses[0])
    teacher_user = make_user("canonscope-teacher", institution, campuses[0], role=SUBJECT_TEACHER)
    employee = make_employee(institution, campuses[0], "CANON-1", user=teacher_user)
    structure = make_structure(admin, institution, campuses[0], "canon")
    teaching_services.assign_teacher(
        admin,
        offering=structure["offering"],
        employee=employee,
        role=TeacherAssignment.Role.LEAD,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        workload_hours=1,
    )
    session = attendance_services.open_session(
        teacher_user, offering=structure["offering"], attendance_date=date(2026, 11, 23)
    )
    assert session.institution_id == institution.id
