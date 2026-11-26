import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.notifications.models import NotificationTemplate
from apps.permissions.models import Role, UserRole
from apps.permissions.roles import PARENT_GUARDIAN, REGISTRAR


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def base(db):
    from apps.institutions.models import Campus, Institution

    institution = Institution.objects.create(code="RBAC2", name="RBAC2")
    campus = Campus.objects.create(institution=institution, code="MAIN", name="Main")
    User = get_user_model()
    parent = User.objects.create_user(
        email="p@r.test",
        password="pass12345",
        institution=institution,
        campus=campus,
    )
    registrar = User.objects.create_user(
        email="r@r.test",
        password="pass12345",
        institution=institution,
        campus=campus,
    )
    Role.objects.get_or_create(name=PARENT_GUARDIAN, defaults={"is_system": True})
    Role.objects.get_or_create(name=REGISTRAR, defaults={"is_system": True})
    UserRole.objects.create(user=parent, role=Role.objects.get(name=PARENT_GUARDIAN))
    UserRole.objects.create(user=registrar, role=Role.objects.get(name=REGISTRAR))
    return institution, campus, parent, registrar


@pytest.mark.django_db
def test_account_create_denies_parent(api_client, base):
    institution, _, parent, _ = base
    api_client.force_authenticate(parent)
    r = api_client.post(
        "/api/v1/accounting/accounts/",
        {
            "institution": str(institution.id),
            "code": "9999",
            "name": "X",
            "account_type": "asset",
        },
        format="json",
    )
    assert r.status_code in {403, 404}


@pytest.mark.django_db
def test_journal_create_denies_parent(api_client, base):
    institution, _, parent, _ = base
    api_client.force_authenticate(parent)
    r = api_client.post(
        "/api/v1/accounting/journal-entries/",
        {"institution": str(institution.id), "reference": "X", "lines": []},
        format="json",
    )
    assert r.status_code in {403, 404}


@pytest.mark.django_db
def test_notification_template_update_denies_parent(api_client, base):
    institution, _, parent, _ = base
    t = NotificationTemplate.objects.create(
        institution=institution,
        code="T1",
        channel=NotificationTemplate.Channel.IN_APP,
        body="b",
    )
    api_client.force_authenticate(parent)
    r = api_client.patch(f"/api/v1/notifications/templates/{t.id}/", {"name": "X"}, format="json")
    assert r.status_code in {403, 404}
