import pytest
from django.contrib.auth import get_user_model

from apps.accounting.models import LedgerAccount
from apps.accounting.services import AccountingError, post_journal_entry
from apps.institutions.models import Institution
from apps.permissions.models import Permission, Role, RolePermission, UserRole


def grant_role(user, *, institution, role_name):
    role, _ = Role.objects.get_or_create(
        name=role_name, defaults={"is_system": True, "institution": institution}
    )
    UserRole.objects.get_or_create(
        user=user,
        role=role,
        scope_type=UserRole.ScopeType.INSTITUTION,
        scope_ref_id=institution.id,
        defaults={"is_active": True},
    )
    for perm in Permission.objects.filter(module="accounting"):
        if role_name in (perm.allowed_role_names or []):
            RolePermission.objects.get_or_create(role=role, permission=perm)


@pytest.mark.django_db
def test_journal_posting_is_balanced_and_idempotent():
    inst = Institution.objects.create(name="Acc Inst", code="ACC")
    user = get_user_model().objects.create_user(
        email="acc@test.local", password="Passw0rd!123", institution=inst
    )
    grant_role(user, institution=inst, role_name="Bursar/Accountant")
    cash = LedgerAccount.objects.create(
        institution=inst, code="1000", name="Cash", account_type="asset"
    )
    income = LedgerAccount.objects.create(
        institution=inst, code="4000", name="Income", account_type="income"
    )
    entry, created = post_journal_entry(
        actor=user,
        institution=inst,
        entry_date="2026-11-24",
        reference="R1",
        idempotency_key="J1",
        lines=[{"account": cash, "debit": "100.00"}, {"account": income, "credit": "100.00"}],
    )
    assert created
    assert entry.status == "posted"
    entry2, created2 = post_journal_entry(
        actor=user,
        institution=inst,
        entry_date="2026-11-24",
        reference="R1",
        idempotency_key="J1",
        lines=[{"account": cash, "debit": "100.00"}, {"account": income, "credit": "100.00"}],
    )
    assert not created2
    assert entry2.id == entry.id


@pytest.mark.django_db
def test_journal_posting_rejects_unbalanced():
    inst = Institution.objects.create(name="Acc2", code="AC2")
    user = get_user_model().objects.create_user(
        email="acc2@test.local", password="Passw0rd!123", institution=inst
    )
    cash = LedgerAccount.objects.create(
        institution=inst, code="1000", name="Cash", account_type="asset"
    )
    income = LedgerAccount.objects.create(
        institution=inst, code="4000", name="Income", account_type="income"
    )
    with pytest.raises(AccountingError):
        post_journal_entry(
            actor=user,
            institution=inst,
            entry_date="2026-11-24",
            lines=[{"account": cash, "debit": "100.00"}, {"account": income, "credit": "90.00"}],
        )
