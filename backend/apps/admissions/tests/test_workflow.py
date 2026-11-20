from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.guardians.models import Guardian
from apps.institutions.models import Campus, Institution
from apps.permissions.models import Role, UserRole
from apps.students.models import Student, StudentGuardian

from ..models import Application
from ..services import (
    DuplicateIdentityError,
    WorkflowError,
    accept_application,
    create_application,
    enrol_application,
    offer_application,
    record_decision,
    review_application,
    submit_application,
)

User = get_user_model()


def setup_school(code="alpha", role_name="Registrar/Admissions", campus_code=None):
    institution = Institution.objects.create(name=code.title(), code=code)
    campus = Campus.objects.create(
        institution=institution,
        name=f"{code.title()} Main",
        code=campus_code or f"{code}-main",
    )
    user = User.objects.create_user(
        email=f"{code}@example.com",
        password="StrongPass123!",
        institution=institution,
        campus=campus,
    )
    role = Role.objects.create(name=role_name, institution=institution)
    UserRole.objects.create(user=user, role=role)
    return institution, campus, user


def applicant_fields(**overrides):
    fields = {
        "first_name": "Amaka",
        "last_name": "Okafor",
        "date_of_birth": date(2015, 5, 10),
        "gender": "female",
        "email": "amaka@example.com",
        "phone": "+2348012345678",
        "intended_class": "Primary 3",
        "cycle": "2026",
    }
    fields.update(overrides)
    return fields


def prepare_accepted_application(institution, campus, user, **overrides):
    application = create_application(
        user,
        institution=institution,
        campus=campus,
        **applicant_fields(**overrides),
    )
    submit_application(user, application)
    review_application(user, application)
    review_application(user, application)
    record_decision(user, application, "approved", notes="meets criteria")
    offer_application(user, application)
    accept_application(user, application)
    application.refresh_from_db()
    return application


@pytest.mark.django_db
def test_full_admission_workflow_creates_unique_student_and_audit_trail():
    institution, campus, user = setup_school()
    application = prepare_accepted_application(institution, campus, user)
    guardian = Guardian.objects.create(
        institution=institution,
        first_name="Ngozi",
        last_name="Okafor",
        phone="+2348098765432",
        email="ngozi@example.com",
    )

    student = enrol_application(
        user,
        application,
        guardian_links=[
            {
                "guardian": guardian,
                "relationship": "Mother",
                "is_primary": True,
                "authorized_pickup": True,
            }
        ],
        reason="guardian accepted offer",
    )

    assert application.application_number.startswith("APP-2026-")
    assert student.admission_number.startswith("ADM-2026-")
    assert student.status == Student.LifecycleStatus.ENROLLED
    assert student.source_application_id == application.id
    application.refresh_from_db()
    assert application.status == Application.Status.ENROLLED
    assert StudentGuardian.objects.filter(student=student, guardian=guardian).count() == 1
    assert AuditLog.objects.filter(action="admissions.enrolment_completed").exists()
    assert AuditLog.objects.filter(action="students.lifecycle_changed").count() == 2
    assert AuditLog.objects.filter(action="admissions.decision_recorded").exists()


@pytest.mark.django_db
def test_enrolment_rejects_duplicate_identity():
    institution, campus, user = setup_school("beta")
    first = prepare_accepted_application(institution, campus, user)
    enrol_application(user, first)

    second = prepare_accepted_application(
        institution,
        campus,
        user,
        email="amaka.other@example.com",
        phone="+2348055555555",
    )
    with pytest.raises(DuplicateIdentityError):
        enrol_application(user, second)

    assert Student.objects.count() == 1
    second.refresh_from_db()
    assert second.status == Application.Status.ACCEPTED


@pytest.mark.django_db
def test_invalid_workflow_transitions_are_rejected():
    institution, campus, user = setup_school("gamma")
    application = create_application(
        user,
        institution=institution,
        campus=campus,
        **applicant_fields(),
    )

    with pytest.raises(WorkflowError):
        record_decision(user, application, "approved")
    with pytest.raises(WorkflowError):
        offer_application(user, application)
    with pytest.raises(WorkflowError):
        enrol_application(user, application)

    assert Student.objects.count() == 0
    assert not AuditLog.objects.filter(action="admissions.enrolment_completed").exists()


@pytest.mark.django_db
def test_api_full_flow_scoping_and_role_denials():
    institution, campus, registrar = setup_school("delta")
    guardian = Guardian.objects.create(
        institution=institution,
        first_name="Chidi",
        last_name="Okafor",
        phone="+2348088888888",
    )
    client = APIClient()
    client.force_login(registrar)

    enquiry_response = client.post(
        "/api/v1/admissions/enquiries/",
        {
            "first_name": "Ifeoma",
            "last_name": "Okafor",
            "date_of_birth": "2014-03-02",
            "gender": "female",
            "email": "ifeoma@example.com",
            "phone": "+2348011111111",
            "intended_class": "Primary 2",
            "source": "walk-in",
        },
        format="json",
    )
    assert enquiry_response.status_code == 201, enquiry_response.data

    application_response = client.post(
        "/api/v1/admissions/applications/",
        {
            "enquiry": enquiry_response.data["id"],
            "first_name": "Ifeoma",
            "last_name": "Okafor",
            "date_of_birth": "2014-03-02",
            "gender": "female",
            "email": "ifeoma@example.com",
            "phone": "+2348011111111",
            "intended_class": "Primary 2",
            "cycle": "2026",
        },
        format="json",
    )
    assert application_response.status_code == 201, application_response.data
    application_id = application_response.data["id"]
    base = f"/api/v1/admissions/applications/{application_id}"

    assert client.post(f"{base}/submit/", {}, format="json").status_code == 200
    assert client.post(
        f"{base}/decide/",
        {"outcome": "approved", "notes": "interview passed"},
        format="json",
    ).status_code == 200
    assert client.post(f"{base}/offer/", {}, format="json").status_code == 200
    assert client.post(f"{base}/accept/", {}, format="json").status_code == 200
    enrol_response = client.post(
        f"{base}/enrol/",
        {
            "guardian_links": [
                {"guardian": str(guardian.id), "relationship": "Father", "is_primary": True}
            ],
            "reason": "offer accepted",
        },
        format="json",
    )
    assert enrol_response.status_code == 200, enrol_response.data

    students_response = client.get("/api/v1/students/")
    assert students_response.status_code == 200
    assert len(students_response.data["results"]) == 1
    student_id = students_response.data["results"][0]["id"]
    assert client.get(f"/api/v1/students/{student_id}/guardians/").status_code == 200

    other_institution, _, other_user = setup_school("epsilon")
    other_client = APIClient()
    other_client.force_login(other_user)
    assert other_client.get(f"{base}/").status_code == 404
    assert other_client.get(f"/api/v1/students/{student_id}/").status_code == 404

    bursar = User.objects.create_user(
        email="bursar@example.com",
        password="StrongPass123!",
        institution=other_institution,
    )
    bursar_role = Role.objects.create(name="Bursar/Accountant", institution=other_institution)
    UserRole.objects.create(user=bursar, role=bursar_role)
    other_client.force_login(bursar)
    denied = other_client.post(
        "/api/v1/admissions/enquiries/",
        {
            "first_name": "Denied",
            "last_name": "User",
            "date_of_birth": "2015-01-01",
        },
        format="json",
    )
    assert denied.status_code == 403
    assert AuditLog.objects.filter(
        action="authz.denied", reason="missing_required_role"
    ).exists()
