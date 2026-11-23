import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from apps.audit.models import AuditLog
from apps.institutions.models import Campus, Institution
from apps.permissions.models import Role, UserRole
from apps.permissions.permissions import (
    HasInstitutionContext,
    IsAuthenticatedAndActive,
    IsCampusScoped,
    IsInstitutionScoped,
)
from apps.permissions.services import (
    get_user_role_names,
    user_has_active_role,
    user_has_active_role_for_institution,
)

User = get_user_model()


@pytest.mark.django_db
def test_user_has_active_role_and_role_names():
    user = User.objects.create_user(email="rbac@example.com", password="StrongPass123!")
    role = Role.objects.create(name="Teacher", is_system=True)
    UserRole.objects.create(user=user, role=role, is_active=True)

    assert user_has_active_role(user, "Teacher") is True
    assert user_has_active_role(user, "Admin") is False
    assert get_user_role_names(user) == ["Subject Teacher"]



@pytest.mark.django_db
def test_is_authenticated_and_active_permission():
    factory = APIRequestFactory()
    request = factory.get("/api/v1/auth/me/")

    inactive = User.objects.create_user(
        email="inactive@example.com", password="StrongPass123!", is_active=False
    )
    active = User.objects.create_user(
        email="active@example.com", password="StrongPass123!", is_active=True
    )
    perm = IsAuthenticatedAndActive()

    request.user = inactive
    assert perm.has_permission(request, None) is False
    request.user = active
    assert perm.has_permission(request, None) is True


@pytest.mark.django_db
def test_has_institution_context_permission():
    factory = APIRequestFactory()
    request = factory.get("/x")
    perm = HasInstitutionContext()

    user = User.objects.create_user(email="nocontext@example.com", password="StrongPass123!")
    request.user = user
    assert perm.has_permission(request, None) is False

    # Superuser bypasses institution-context requirement in foundation guard
    su = User.objects.create_superuser(email="admin@example.com", password="StrongPass123!")
    request.user = su
    assert perm.has_permission(request, None) is True


@pytest.mark.django_db
def test_active_role_institution_validation():
    inst_a = Institution.objects.create(name="Alpha", code="alpha")
    inst_b = Institution.objects.create(name="Beta", code="beta")

    user = User.objects.create_user(
        email="scoped@example.com", password="StrongPass123!", institution=inst_a
    )
    role_a = Role.objects.create(name="Admin", institution=inst_a)
    role_b = Role.objects.create(name="Admin", institution=inst_b)
    assert user_has_active_role_for_institution(user, inst_a.id) is False

    assignment_a = UserRole.objects.create(user=user, role=role_a)
    assert user_has_active_role_for_institution(user, inst_a.id) is True
    assert user_has_active_role_for_institution(user, inst_b.id) is False

    assignment_a.is_active = False
    assignment_a.save(update_fields=["is_active"])
    assert user_has_active_role_for_institution(user, inst_a.id) is False

    UserRole.objects.create(user=user, role=role_b, is_active=True)
    assert user_has_active_role_for_institution(user, inst_b.id) is False

    global_role = Role.objects.create(name="Global", is_system=True)
    UserRole.objects.create(user=user, role=global_role)
    assert user_has_active_role_for_institution(user, inst_a.id) is True
    assert user_has_active_role_for_institution(user, inst_b.id) is False


@pytest.mark.django_db
def test_object_level_scope_denials_are_audited():
    inst_a = Institution.objects.create(name="Alpha", code="alpha")
    inst_b = Institution.objects.create(name="Beta", code="beta")
    campus_a = Campus.objects.create(institution=inst_a, name="Main", code="main")
    campus_b = Campus.objects.create(institution=inst_b, name="Other", code="other")

    user = User.objects.create_user(
        email="objectscope@example.com",
        password="StrongPass123!",
        institution=inst_a,
        campus=campus_a,
    )
    UserRole.objects.create(
        user=user, role=Role.objects.create(name="Admin", institution=inst_a)
    )
    request = APIRequestFactory().get("/x")
    request.user = user

    assert IsInstitutionScoped().has_object_permission(request, None, inst_a) is True
    assert IsInstitutionScoped().has_object_permission(request, None, inst_b) is False
    assert IsCampusScoped().has_object_permission(request, None, campus_a) is True
    assert IsCampusScoped().has_object_permission(request, None, campus_b) is False

    assert AuditLog.objects.filter(
        action="authz.denied", reason="cross_institution_access"
    ).exists()
    assert AuditLog.objects.filter(
        action="authz.denied", reason="cross_campus_access"
    ).exists()
