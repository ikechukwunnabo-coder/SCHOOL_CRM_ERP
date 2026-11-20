from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.guardians.models import Guardian
from apps.institutions.models import Campus, Institution
from apps.permissions.models import Role, UserRole
from apps.students.models import Student

from ..services import StudentWorkflowError, change_lifecycle, link_guardian

User = get_user_model()


def setup_student():
    institution = Institution.objects.create(name="Zeta", code="zeta")
    campus = Campus.objects.create(institution=institution, name="Main", code="zeta-main")
    user = User.objects.create_user(
        email="registrar@zeta.example.com",
        password="StrongPass123!",
        institution=institution,
        campus=campus,
    )
    role = Role.objects.create(name="Registrar/Admissions", institution=institution)
    UserRole.objects.create(user=user, role=role)
    student = Student.objects.create(
        institution=institution,
        campus=campus,
        admission_number="ADM-2026-000001",
        first_name="Tobi",
        last_name="Adeyemi",
        date_of_birth=date(2014, 8, 12),
        admission_date=date(2026, 1, 15),
        status=Student.LifecycleStatus.ADMITTED,
    )
    return institution, student, user


@pytest.mark.django_db
def test_lifecycle_transitions_are_validated_audited_and_historical():
    _, student, user = setup_student()

    with pytest.raises(StudentWorkflowError):
        change_lifecycle(
            user,
            student,
            Student.LifecycleStatus.GRADUATED,
            effective_date=date(2026, 1, 16),
            reason="invalid",
        )

    change_lifecycle(
        user,
        student,
        Student.LifecycleStatus.ENROLLED,
        effective_date=date(2026, 1, 16),
        reason="enrolment",
    )
    change_lifecycle(
        user,
        student,
        Student.LifecycleStatus.ACTIVE,
        effective_date=date(2026, 1, 20),
        reason="session started",
    )
    student.refresh_from_db()

    assert student.status == Student.LifecycleStatus.ACTIVE
    assert student.lifecycle_events.count() == 2
    assert list(
        student.lifecycle_events.order_by("effective_date").values_list("to_status", flat=True)
    ) == ["enrolled", "active"]
    assert AuditLog.objects.filter(
        action="students.lifecycle_changed",
        target_id=str(student.pk),
    ).count() == 2


@pytest.mark.django_db
def test_duplicate_guardian_link_is_rejected():
    institution, student, user = setup_student()
    guardian = Guardian.objects.create(
        institution=institution,
        first_name="Bola",
        last_name="Adeyemi",
        phone="+2348077777777",
    )
    link_guardian(user, student, guardian, relationship="Mother", is_primary=True)

    with pytest.raises(StudentWorkflowError):
        link_guardian(user, student, guardian, relationship="Mother")

    assert student.guardian_links.count() == 1


@pytest.mark.django_db
def test_api_rejects_invalid_lifecycle_transition_with_conflict():
    _, student, user = setup_student()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1/students/{student.id}/lifecycle/",
        {
            "to_status": "graduated",
            "effective_date": "2026-01-16",
            "reason": "too early",
        },
        format="json",
    )
    assert response.status_code == 409
    student.refresh_from_db()
    assert student.status == Student.LifecycleStatus.ADMITTED
