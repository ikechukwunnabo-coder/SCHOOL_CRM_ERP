from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounting.models import LedgerAccount
from apps.accounting.services import create_journal_entry
from apps.notifications.models import Notification, NotificationTemplate
from apps.permissions.models import Role, UserRole
from apps.permissions.roles import PARENT_GUARDIAN


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def base(db):
    from apps.institutions.models import Campus, Institution

    institution = Institution.objects.create(code="RBAC4", name="RBAC4")
    campus = Campus.objects.create(institution=institution, code="MAIN", name="Main")
    User = get_user_model()
    parent = User.objects.create_user(
        email="p4@r.test", password="pass12345", institution=institution, campus=campus
    )
    bursar = User.objects.create_user(
        email="b4@r.test", password="pass12345", institution=institution, campus=campus
    )
    Role.objects.get_or_create(name=PARENT_GUARDIAN, defaults={"is_system": True})
    Role.objects.get_or_create(name="Bursar/Accountant", defaults={"is_system": True})
    UserRole.objects.create(user=parent, role=Role.objects.get(name=PARENT_GUARDIAN))
    UserRole.objects.create(user=bursar, role=Role.objects.get(name="Bursar/Accountant"))
    cash = LedgerAccount.objects.create(institution=institution, code="1000", name="Cash")
    income = LedgerAccount.objects.create(institution=institution, code="4000", name="Income")
    return institution, campus, parent, bursar, cash, income


@pytest.mark.django_db
def test_account_delete_denies_parent(api_client, base):
    institution, _, parent, _, cash, _ = base
    api_client.force_authenticate(parent)
    r = api_client.delete(f"/api/v1/accounting/accounts/{cash.id}/")
    assert r.status_code in {403, 404}


@pytest.mark.django_db
def test_journal_detail_denies_parent(api_client, base):
    institution, campus, parent, bursar, cash, income = base
    entry, _ = create_journal_entry(
        actor=bursar,
        institution=institution,
        campus=campus,
        entry_date=timezone.localdate(),
        reference="RBAC4-1",
        description="d",
        lines=[
            {"account": cash, "debit": Decimal("1.00"), "credit": Decimal("0")},
            {"account": income, "debit": Decimal("0"), "credit": Decimal("1.00")},
        ],
    )
    api_client.force_authenticate(parent)
    r = api_client.get(f"/api/v1/accounting/journal-entries/{entry.id}/")
    assert r.status_code in {403, 404}


@pytest.mark.django_db
def test_notification_logs_list_denies_parent(api_client, base):
    institution, campus, parent, _, _, _ = base
    Notification.objects.create(
        institution=institution,
        campus=campus,
        channel=NotificationTemplate.Channel.IN_APP,
        body="b",
        status=Notification.Status.SENT,
    )
    api_client.force_authenticate(parent)
    r = api_client.get("/api/v1/notifications/logs/")
    assert r.status_code in {403, 404}
