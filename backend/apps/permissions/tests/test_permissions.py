import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from apps.permissions.models import Role, UserRole
from apps.permissions.permissions import HasInstitutionContext, IsAuthenticatedAndActive
from apps.permissions.services import get_user_role_names, user_has_active_role

User = get_user_model()


@pytest.mark.django_db
def test_user_has_active_role_and_role_names():
    user = User.objects.create_user(email="rbac@example.com", password="StrongPass123!")
    role = Role.objects.create(name="Teacher", is_system=True)
    UserRole.objects.create(user=user, role=role, is_active=True)

    assert user_has_active_role(user, "Teacher") is True
    assert user_has_active_role(user, "Admin") is False
    assert get_user_role_names(user) == ["Teacher"]


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
