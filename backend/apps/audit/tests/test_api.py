import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.audit.services import log_event
from apps.permissions.models import Role, UserRole
from apps.permissions.roles import PARENT_GUARDIAN, SUPER_ADMIN


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def base(db):
    from apps.institutions.models import Campus, Institution

    inst = Institution.objects.create(code="AUD", name="Audit Inst")
    campus = Campus.objects.create(institution=inst, code="MAIN", name="Main")
    User = get_user_model()
    admin = User.objects.create_user(
        email="sa@aud.test", password="pass12345", institution=inst, campus=campus
    )
    parent = User.objects.create_user(
        email="p@aud.test", password="pass12345", institution=inst, campus=campus
    )
    Role.objects.get_or_create(name=SUPER_ADMIN, defaults={"is_system": True})
    Role.objects.get_or_create(name=PARENT_GUARDIAN, defaults={"is_system": True})
    UserRole.objects.create(user=admin, role=Role.objects.get(name=SUPER_ADMIN))
    UserRole.objects.create(user=parent, role=Role.objects.get(name=PARENT_GUARDIAN))
    log_event("audit.visible", actor=admin, institution_id=inst.id, campus_id=campus.id)
    return inst, admin, parent


@pytest.mark.django_db
def test_audit_log_list_denies_parent(api_client, base):
    _, _, parent = base
    api_client.force_authenticate(parent)
    r = api_client.get("/api/v1/audit/logs/")
    assert r.status_code in {403, 404}


@pytest.mark.django_db
def test_audit_log_list_allows_admin(api_client, base):
    _, admin, _ = base
    api_client.force_authenticate(admin)
    r = api_client.get("/api/v1/audit/logs/")
    assert r.status_code == 200
    assert r.data["count"] >= 1
