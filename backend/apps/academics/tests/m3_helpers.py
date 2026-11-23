from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.employees.models import Employee
from apps.institutions.models import Campus, Institution
from apps.permissions.models import Role, UserRole
from apps.permissions.roles import INSTITUTION_ADMIN
from apps.students.models import Student

from .. import services as academic_services

User = get_user_model()


def make_school(code, campus_codes=("main",)):
    institution = Institution.objects.create(name=code.title(), code=code)
    campuses = [
        Campus.objects.create(
            institution=institution,
            name=f"{code.title()} {campus_code}",
            code=f"{code}-{campus_code}",
        )
        for campus_code in campus_codes
    ]
    return institution, campuses


def grant_role(user, institution, name, scope_type="institution"):
    role, _ = Role.objects.get_or_create(name=name, institution=institution)
    return UserRole.objects.create(
        user=user, role=role, scope_type=scope_type, is_active=True
    )


def make_user(code, institution, campus=None, role=INSTITUTION_ADMIN, role_institution=None):
    user = User.objects.create_user(
        email=f"{code}@example.com",
        password="StrongPass123!",
        institution=institution,
        campus=campus,
    )
    grant_role(user, role_institution or institution, role)
    return user


def client_for(user):
    client = APIClient()
    client.force_login(user)
    return client


def make_employee(institution, campus, code, user=None):
    return Employee.objects.create(
        institution=institution,
        campus=campus,
        user=user,
        employee_number=f"EMP-{code}",
        first_name="Ada",
        last_name="Obi",
    )


def make_student(institution, campus, code):
    return Student.objects.create(
        institution=institution,
        campus=campus,
        admission_number=f"ADM-{code}",
        first_name=f"Chidi-{code}",
        last_name="Okafor-{code}",
        date_of_birth=date(2015, 4, 12),
        gender="male",
        admission_date=date(2026, 1, 8),
    )


def make_structure(actor, institution, campus, prefix, *, student=False):
    session = academic_services.create_session(
        actor,
        institution=institution,
        campus=campus,
        name=f"{prefix.upper()} Session",
        code=f"{prefix}-2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    term = academic_services.create_term(
        actor,
        session=session,
        name="First Term",
        code=f"{prefix}-T1",
        start_date=date(2026, 1, 8),
        end_date=date(2026, 12, 20),
    )
    level = academic_services.create_class_level(
        actor,
        institution=institution,
        campus=campus,
        name="Primary 4",
        code=f"{prefix}-P4",
    )
    arm = academic_services.create_arm(
        actor, class_level=level, name="Gold", code=f"{prefix}-G"
    )
    subject = academic_services.create_subject(
        actor, institution=institution, name="Mathematics", code=f"{prefix}-MTH"
    )
    offering = academic_services.create_offering(
        actor,
        session=session,
        term=term,
        class_level=level,
        arm=arm,
        subject=subject,
    )
    enrolment = None
    if student:
        enrolment = academic_services.enrol_student(
            actor,
            session=session,
            class_level=level,
            arm=arm,
            student=make_student(institution, campus, f"{prefix}-S1"),
        )
    return {
        "session": session,
        "term": term,
        "level": level,
        "arm": arm,
        "subject": subject,
        "offering": offering,
        "enrolment": enrolment,
    }
