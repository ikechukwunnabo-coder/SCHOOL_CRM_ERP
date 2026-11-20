import pytest
from django.contrib.auth import get_user_model

from apps.institutions.models import Campus, Institution
from apps.permissions.models import Role, UserRole
from apps.permissions.services import get_user_role_names, user_has_module_permission

User = get_user_model()


@pytest.mark.django_db
def test_per_verb_grants_are_configurable_and_deny_by_default():
    institution = Institution.objects.create(name="Grant", code="grant")
    campus = Campus.objects.create(institution=institution, name="Main", code="grant-main")
    user = User.objects.create_user(
        email="user@grant.example.com",
        password="StrongPass123!",
        institution=institution,
        campus=campus,
    )
    role = Role.objects.create(name="Bursar/Accountant", institution=institution)
    UserRole.objects.create(user=user, role=role)

    assert get_user_role_names(user) == ["Bursar/Accountant"]
    assert user_has_module_permission(user, "admissions", "view")
    assert not user_has_module_permission(user, "admissions", "submit")
    assert not user_has_module_permission(user, "admissions", "approve")
    assert not user_has_module_permission(user, "imports", "import")
    assert user_has_module_permission(user, "students", "view")
