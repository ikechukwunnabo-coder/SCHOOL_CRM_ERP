import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.permissions.models import Role, UserRole
from apps.permissions.roles import PARENT_GUARDIAN


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def base(db):
    from apps.institutions.models import Campus, Institution

    institution = Institution.objects.create(code="RBAC6", name="RBAC6")
    campus = Campus.objects.create(institution=institution, code="MAIN", name="Main")
    User = get_user_model()
    parent = User.objects.create_user(
        email="p6@r.test", password="pass12345", institution=institution, campus=campus
    )
    Role.objects.get_or_create(name=PARENT_GUARDIAN, defaults={"is_system": True})
    UserRole.objects.create(user=parent, role=Role.objects.get(name=PARENT_GUARDIAN))
    return institution, campus, parent


@pytest.mark.django_db
def test_fee_schedule_create_denies_parent(api_client, base):
    institution, _, parent = base
    api_client.force_authenticate(parent)
    r = api_client.post(
        "/api/v1/finance/fee-schedules/",
        {
            "institution": str(institution.id),
            "name": "X",
            "items": [],
        },
        format="json",
    )
    assert r.status_code in {400, 403, 404}
