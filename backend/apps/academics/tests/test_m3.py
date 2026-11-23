from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.attendance import services as attendance_services
from apps.attendance.models import AttendanceRecord
from apps.audit.models import AuditLog
from apps.employees.models import Employee
from apps.institutions.models import Campus, Institution
from apps.permissions.models import Role, UserRole
from apps.students.models import Student
from apps.teaching import services as teaching_services
from apps.teaching.models import TeacherAssignment

from .. import services
from ..models import ClassEnrolment

User = get_user_model()


def setup_school(code="m3", teacher=True):
    institution = Institution.objects.create(name=code.title(), code=code)
    campus = Campus.objects.create(
        institution=institution, name=f"{code.title()} Main", code=f"{code}-main"
    )
    admin = User.objects.create_user(
        email=f"admin-{code}@example.com",
        password="StrongPass123!",
        institution=institution,
        campus=campus,
    )
    admin_role = Role.objects.create(name="Institution Administrator", institution=institution)
    UserRole.objects.create(user=admin, role=admin_role)
    teacher_user = None
    teacher_employee = None
    if teacher:
        teacher_user = User.objects.create_user(
            email=f"teacher-{code}@example.com",
            password="StrongPass123!",
            institution=institution,
            campus=campus,
        )
        teacher_role = Role.objects.create(name="Teacher", institution=institution)
        UserRole.objects.create(user=teacher_user, role=teacher_role)
        teacher_employee = Employee.objects.create(
            institution=institution,
            campus=campus,
            user=teacher_user,
            employee_number=f"EMP-{code}-001",
            first_name="Ada",
            last_name="Obi",
        )
    return institution, campus, admin, teacher_user, teacher_employee


def setup_structure(institution, campus, admin, prefix="m3"):
    session = services.create_session(
        admin,
        institution=institution,
        campus=campus,
        name=f"{prefix.upper()} Session",
        code=f"{prefix}-2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    term = services.create_term(
        admin,
        session=session,
        name="First Term",
        code=f"{prefix}-T1",
        start_date=date(2026, 1, 8),
        end_date=date(2026, 12, 20),
    )
    level = services.create_class_level(
        admin, institution=institution, campus=campus, name="Primary 4", code=f"{prefix}-P4"
    )
    arm = services.create_arm(admin, class_level=level, name="Gold", code="G")
    subject = services.create_subject(
        admin, institution=institution, name="Mathematics", code=f"{prefix}-MTH"
    )
    offering = services.create_offering(
        admin, session=session, term=term, class_level=level, arm=arm, subject=subject
    )
    return session, term, level, arm, subject, offering


def create_student(institution, campus, code):
    return Student.objects.create(
        institution=institution,
        campus=campus,
        admission_number=f"ADM-{code}",
        first_name="Chidi",
        last_name="Okafor",
        date_of_birth=date(2015, 4, 12),
        gender="male",
        admission_date=date(2026, 1, 8),
    )


@pytest.mark.django_db
def test_academic_structure_and_enrolment_are_audited():
    institution, campus, admin, _, _ = setup_school("acad")
    session, term, level, arm, subject, offering = setup_structure(
        institution, campus, admin, "acad"
    )
    student = create_student(institution, campus, "ACAD-001")
    enrolment = services.enrol_student(
        admin, session=session, class_level=level, arm=arm, student=student
    )

    assert term.session_id == session.id
    assert offering.arm_id == arm.id
    assert offering.subject_id == subject.id
    assert enrolment.status == ClassEnrolment.Status.ACTIVE
    assert AuditLog.objects.filter(action="academics.session_created").exists()
    assert AuditLog.objects.filter(action="academics.offering_created").exists()
    assert AuditLog.objects.filter(action="academics.student_enrolled").exists()


@pytest.mark.django_db
def test_teacher_reassignment_and_timetable_conflict_checks():
    institution, campus, admin, _, teacher_employee = setup_school("teach")
    session, term, level, arm, subject, offering = setup_structure(
        institution, campus, admin, "teach"
    )
    second_employee = Employee.objects.create(
        institution=institution,
        campus=campus,
        employee_number="EMP-TEACH-002",
        first_name="Ngozi",
        last_name="Eze",
    )
    today = timezone.localdate()
    assignment = teaching_services.assign_teacher(
        admin,
        offering=offering,
        employee=teacher_employee,
        role=TeacherAssignment.Role.LEAD,
        start_date=today - timedelta(days=1),
        end_date=today + timedelta(days=30),
        workload_hours=2,
    )
    replacement = teaching_services.assign_teacher(
        admin,
        offering=offering,
        employee=second_employee,
        role=TeacherAssignment.Role.LEAD,
        start_date=today,
        end_date=today + timedelta(days=30),
        workload_hours=2,
        reassign=True,
    )
    assignment.refresh_from_db()
    assert assignment.status == TeacherAssignment.Status.CLOSED
    assert replacement.status == TeacherAssignment.Status.ACTIVE

    timetable = teaching_services.create_timetable(
        admin, session=session, class_level=level, arm=arm, name="Term 1"
    )
    second_subject = services.create_subject(
        admin, institution=institution, name="English", code="TEACH-ENG"
    )
    second_offering = services.create_offering(
        admin,
        session=session,
        term=term,
        class_level=level,
        arm=arm,
        subject=second_subject,
    )
    teaching_services.add_slot(
        admin,
        timetable=timetable,
        day_of_week=1,
        period=1,
        offering=offering,
        employee=second_employee,
        room="Room A",
    )
    with pytest.raises(teaching_services.TeachingError, match="teacher_double_booked"):
        teaching_services.add_slot(
            admin,
            timetable=timetable,
            day_of_week=1,
            period=1,
            offering=second_offering,
            employee=second_employee,
            room="Room B",
        )
    assert AuditLog.objects.filter(action="teaching.assignment_created").count() == 2
    assert AuditLog.objects.filter(action="teaching.slot_created").exists()


@pytest.mark.django_db
def test_attendance_teacher_scope_marking_and_corrections():
    institution, campus, admin, teacher_user, teacher_employee = setup_school("att")
    session, term, level, arm, subject, offering = setup_structure(
        institution, campus, admin, "att"
    )
    today = timezone.localdate()
    teaching_services.assign_teacher(
        admin,
        offering=offering,
        employee=teacher_employee,
        role=TeacherAssignment.Role.LEAD,
        start_date=today - timedelta(days=1),
        end_date=today + timedelta(days=30),
        workload_hours=1,
    )
    student = create_student(institution, campus, "ATT-001")
    services.enrol_student(admin, session=session, class_level=level, arm=arm, student=student)

    attendance = attendance_services.open_session(
        teacher_user, offering=offering, attendance_date=today
    )
    record = attendance_services.mark_attendance(
        teacher_user,
        attendance=attendance,
        student=student,
        status=AttendanceRecord.Status.PRESENT,
    )
    assert record.status == AttendanceRecord.Status.PRESENT
    assert attendance_services.expected_students(attendance) == [student]
    assert AuditLog.objects.filter(action="attendance.marked").exists()

    with pytest.raises(attendance_services.AttendanceError, match="correction_not_permitted"):
        attendance_services.correct_attendance(
            teacher_user, record=record, new_status="absent", reason="teacher override"
        )

    correction = attendance_services.correct_attendance(
        admin, record=record, new_status="absent", reason="verified register error"
    )
    record.refresh_from_db()
    assert record.status == AttendanceRecord.Status.ABSENT
    assert record.correction_count == 1
    assert correction.previous_status == AttendanceRecord.Status.PRESENT
    assert AuditLog.objects.filter(action="attendance.corrected").exists()


@pytest.mark.django_db
def test_unassigned_teacher_cannot_open_attendance():
    institution, campus, admin, _, _ = setup_school("unassigned")
    _, _, _, _, _, offering = setup_structure(institution, campus, admin, "unassigned")
    other_user = User.objects.create_user(
        email="unassigned-teacher@example.com",
        password="StrongPass123!",
        institution=institution,
        campus=campus,
    )
    role, _ = Role.objects.get_or_create(name="Teacher", institution=institution)
    UserRole.objects.create(user=other_user, role=role)

    with pytest.raises(
        attendance_services.AttendanceError, match="teacher_not_assigned_to_offering"
    ):
        attendance_services.open_session(
            other_user, offering=offering, attendance_date=timezone.localdate()
        )
