from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.tests.m3_helpers import (
    make_employee,
    make_school,
    make_structure,
    make_user,
)
from apps.permissions.models import Role, UserRole
from apps.permissions.roles import PARENT_GUARDIAN, SUBJECT_TEACHER
from apps.teaching import services as teaching_services
from apps.teaching.models import TeacherAssignment


@pytest.mark.django_db
def test_teacher_portal_returns_assignments_for_teacher_user():
    institution, campuses = make_school("teachportal", ("main",))
    admin = make_user("tp-admin", institution, campuses[0])
    teacher_user = make_user("tp-teacher", institution, campuses[0])
    Role.objects.get_or_create(name=SUBJECT_TEACHER, defaults={"is_system": True})
    UserRole.objects.create(user=teacher_user, role=Role.objects.get(name=SUBJECT_TEACHER))
    employee = make_employee(institution, campuses[0], "TP-1")
    employee.user = teacher_user
    employee.save(update_fields=["user"])
    structure = make_structure(admin, institution, campuses[0], "tp")
    today = timezone.localdate()
    teaching_services.assign_teacher(
        admin,
        offering=structure["offering"],
        employee=employee,
        role=TeacherAssignment.Role.LEAD,
        start_date=today - timedelta(days=1),
        end_date=today + timedelta(days=30),
        workload_hours=5,
    )
    client = APIClient()
    client.force_authenticate(user=teacher_user)
    response = client.get("/api/v1/portal/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["teacher"]["assignment_count"] == 1
    assert len(response.data["assignments"]) == 1


@pytest.mark.django_db
def test_teacher_portal_denies_parent_role():
    institution, campuses = make_school("teachportaldeny", ("main",))
    parent = make_user("tp-parent", institution, campuses[0])
    Role.objects.get_or_create(name=PARENT_GUARDIAN, defaults={"is_system": True})
    UserRole.objects.create(user=parent, role=Role.objects.get(name=PARENT_GUARDIAN))
    client = APIClient()
    client.force_authenticate(user=parent)
    response = client.get("/api/v1/portal/")
    assert response.status_code == status.HTTP_403_FORBIDDEN
