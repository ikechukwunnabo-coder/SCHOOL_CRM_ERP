from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from apps.accounting.models import JournalEntry, LedgerAccount
from apps.accounting.services import AccountingError, create_journal_entry, post_journal_entry
from apps.permissions.models import Role, UserRole
from apps.permissions.roles import PARENT_GUARDIAN


@pytest.fixture
def accounting_base(db):
    from apps.institutions.models import Campus, Institution


    institution = Institution.objects.create(code="ACCT", name="Acct Inst")
    campus = Campus.objects.create(institution=institution, code="MAIN", name="Main")
    from django.contrib.auth import get_user_model

    User = get_user_model()
    bursar = User.objects.create_user(
        email="bursar@acct.test",
        password="pass12345",
        institution=institution,
        campus=campus,
    )
    parent = User.objects.create_user(
        email="parent@acct.test",
        password="pass12345",
        institution=institution,
        campus=campus,
    )
    Role.objects.get_or_create(name="Bursar/Accountant", defaults={"is_system": True})
    Role.objects.get_or_create(name=PARENT_GUARDIAN, defaults={"is_system": True})
    UserRole.objects.create(user=bursar, role=Role.objects.get(name="Bursar/Accountant"))
    UserRole.objects.create(user=parent, role=Role.objects.get(name=PARENT_GUARDIAN))
    cash = LedgerAccount.objects.create(
        institution=institution, code="1000", name="Cash"
    )
    income = LedgerAccount.objects.create(
        institution=institution, code="4000", name="Income"
    )
    return institution, campus, bursar, parent, cash, income


@pytest.mark.django_db
def test_journal_entry_must_balance(accounting_base):
    institution, campus, bursar, _, cash, income = accounting_base
    with pytest.raises(AccountingError, match="journal_not_balanced"):
        create_journal_entry(
            actor=bursar,
            institution=institution,
            campus=campus,
            entry_date=timezone.localdate(),
            reference="REF-1",
            description="Bad",
            lines=[
                {"account": cash, "debit": Decimal("100.00"), "credit": Decimal("0")},
                {"account": income, "debit": Decimal("0"), "credit": Decimal("90.00")},
            ],
        )


@pytest.mark.django_db
def test_journal_entry_post_is_idempotent(accounting_base):
    institution, campus, bursar, _, cash, income = accounting_base
    entry, _ = create_journal_entry(
        actor=bursar,
        institution=institution,
        campus=campus,
        entry_date=timezone.localdate(),
        reference="REF-2",
        description="Good",
        lines=[
            {"account": cash, "debit": Decimal("100.00"), "credit": Decimal("0")},
            {"account": income, "debit": Decimal("0"), "credit": Decimal("100.00")},
        ],
    )
    posted, _ = post_journal_entry(
        actor=bursar,
        institution=institution,
        campus=campus,
        entry_date=timezone.localdate(),
        reference="REF-2",
        description="Good",
        lines=[
            {"account": cash, "debit": Decimal("100.00"), "credit": Decimal("0")},
            {"account": income, "debit": Decimal("0"), "credit": Decimal("100.00")},
        ],
        idempotency_key="ref-2-post",
    )
    assert posted.status == JournalEntry.Status.POSTED
    assert posted.lines.count() == 2
    again, created = post_journal_entry(
        actor=bursar,
        institution=institution,
        campus=campus,
        entry_date=timezone.localdate(),
        reference="REF-2",
        description="Good",
        lines=[
            {"account": cash, "debit": Decimal("100.00"), "credit": Decimal("0")},
            {"account": income, "debit": Decimal("0"), "credit": Decimal("100.00")},
        ],
        idempotency_key="ref-2-post",
    )
    assert again.status == JournalEntry.Status.POSTED
    assert not created


@pytest.mark.django_db
def test_accounting_dashboard_denies_parent(accounting_base):
    from rest_framework.test import APIClient

    _, _, _, parent, _, _ = accounting_base
    client = APIClient()
    client.force_authenticate(user=parent)
    response = client.get("/api/v1/accounting/dashboard/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_accounting_dashboard_allows_bursar(accounting_base):
    from rest_framework.test import APIClient

    _, _, bursar, _, _, _ = accounting_base
    client = APIClient()
    client.force_authenticate(user=bursar)
    response = client.get("/api/v1/accounting/dashboard/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["accounts"]["count"] == 2
@pytest.mark.django_db
def test_journal_approve_requires_approve_permission(accounting_base):
    from rest_framework.test import APIClient

    institution, campus, bursar, _, cash, income = accounting_base
    entry, _ = create_journal_entry(
        actor=bursar,
        institution=institution,
        campus=campus,
        entry_date=timezone.localdate(),
        reference="REF-3",
        description="Needs approval",
        lines=[
            {"account": cash, "debit": Decimal("50.00"), "credit": Decimal("0")},
            {"account": income, "debit": Decimal("0"), "credit": Decimal("50.00")},
        ],
    )
    client = APIClient()
    client.force_authenticate(user=bursar)
    response = client.post(f"/api/v1/accounting/journal-entries/{entry.id}/approve/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_accounting_dashboard_denies_unauthenticated():
    from rest_framework.test import APIClient

    client = APIClient()
    response = client.get("/api/v1/accounting/dashboard/")
    assert response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}
