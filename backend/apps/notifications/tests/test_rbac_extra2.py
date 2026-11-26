import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounting.models import LedgerAccount
from apps.notifications.models import NotificationTemplate
from apps.permissions.models import Role, UserRole
from apps.permissions.roles import PARENT_GUARDIAN, REGISTRAR


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def base(db):
    from apps.institutions.models import Campus, Institution

    institution = Institution.objects.create(code="RBAC3", name="RBAC3")
    campus = Campus.objects.create(institution=institution, code="MAIN", name="Main")
    User = get_user_model()
    parent = User.objects.create_user(
        email="p3@r.test",
        password="pass12345",
        institution=institution,
        campus=campus,
    )
    Role.objects.get_or_create(name=PARENT_GUARDIAN, defaults={"is_system": True})
    Role.objects.get_or_create(name=REGISTRAR, defaults={"is_system": True})
    UserRole.objects.create(user=parent, role=Role.objects.get(name=PARENT_GUARDIAN))
    return institution, campus, parent


@pytest.mark.django_db
def test_account_update_denies_parent(api_client, base):
    institution, _, parent = base
    acct = LedgerAccount.objects.create(
        institution=institution, code="1001", name="Cash", account_type="asset"
    )
    api_client.force_authenticate(parent)
    r = api_client.patch(f"/api/v1/accounting/accounts/{acct.id}/", {"name": "X"}, format="json")
    assert r.status_code in {403, 404}


@pytest.mark.django_db
def test_notification_template_delete_denies_parent(api_client, base):
    institution, _, parent = base
    t = NotificationTemplate.objects.create(
        institution=institution,
        code="TD1",
        channel=NotificationTemplate.Channel.IN_APP,
        body="b",
    )
    api_client.force_authenticate(parent)
    r = api_client.delete(f"/api/v1/notifications/templates/{t.id}/")
    assert r.status_code in {403, 404}
