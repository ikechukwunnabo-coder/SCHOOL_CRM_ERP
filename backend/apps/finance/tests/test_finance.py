import hashlib
import hmac
import json
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from apps.academics.models import AcademicSession
from apps.finance.models import (
    FeeCategory,
    FinancialAdjustment,
    Invoice,
    Payment,
    PaymentWebhookEvent,
)
from apps.finance.services import create_invoice, issue_invoice, record_payment
from apps.institutions.models import Campus, Institution
from apps.permissions.models import Permission, Role, RolePermission, UserRole
from apps.students.models import Student


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def institution(db):
    return Institution.objects.create(name="Finance Inst", code="FIN")


@pytest.fixture
def campus(institution):
    return Campus.objects.create(institution=institution, name="Main Campus", code="MAIN")


@pytest.fixture
def session(institution):
    return AcademicSession.objects.create(
        institution=institution,
        name="2026/2027",
        start_date="2026-09-01",
        end_date="2027-07-31",
    )


@pytest.fixture
def student(institution, campus):
    return Student.objects.create(
        institution=institution,
        campus=campus,
        admission_number="ADM-FIN-001",
        first_name="Ada",
        last_name="Okafor",
        date_of_birth=__import__("datetime").date(2012, 1, 1),
        admission_date=__import__("datetime").date(2026, 9, 1),
        status=Student.LifecycleStatus.ENROLLED,
    )


def grant_role(user, *, institution, campus, role_name, module="finance"):
    role, _ = Role.objects.get_or_create(
        name=role_name, defaults={"is_system": True, "institution": institution}
    )
    UserRole.objects.get_or_create(
        user=user,
        role=role,
        scope_type=UserRole.ScopeType.CAMPUS,
        scope_ref_id=campus.id,
        defaults={"is_active": True},
    )
    for perm in Permission.objects.filter(module=module):
        if role_name in (perm.allowed_role_names or []):
            RolePermission.objects.get_or_create(role=role, permission=perm)


@pytest.fixture
def accountant(db, institution, campus):
    user = get_user_model().objects.create_user(
        email="acct@fin.test", password="Passw0rd!123", institution=institution, campus=campus
    )
    grant_role(user, institution=institution, campus=campus, role_name="Bursar/Accountant")
    return user


@pytest.fixture
def principal(db, institution, campus):
    user = get_user_model().objects.create_user(
        email="principal@fin.test", password="Passw0rd!123", institution=institution, campus=campus
    )
    grant_role(user, institution=institution, campus=campus, role_name="Principal/Head Teacher")
    return user


@pytest.mark.django_db
def test_invoice_issue_and_payment_allocation_updates_balance(
    institution, campus, session, student, accountant
):
    category = FeeCategory.objects.create(
        institution=institution, campus=campus, code="TUI", name="Tuition"
    )
    invoice = create_invoice(
        actor=accountant,
        institution=institution,
        campus=campus,
        student=student,
        session=session,
        lines=[
            {
                "description": "Tuition",
                "quantity": "1",
                "unit_amount": "100000.00",
                "category": category,
            }
        ],
    )
    issued = issue_invoice(actor=accountant, invoice=invoice)
    assert issued.status == Invoice.Status.ISSUED

    payment = record_payment(
        actor=accountant,
        institution=institution,
        student=student,
        campus=campus,
        amount=Decimal("40000.00"),
        allocations=[{"invoice": issued, "amount": "40000.00"}],
    )
    issued.refresh_from_db()
    assert payment.status == Payment.Status.VERIFIED
    assert issued.status == Invoice.Status.PARTIALLY_PAID
    assert issued.balance_amount == Decimal("60000.00")


@pytest.mark.django_db
def test_payment_idempotency_key_returns_same_payment(
    institution, campus, student, accountant, session
):
    invoice = create_invoice(
        actor=accountant,
        institution=institution,
        campus=campus,
        student=student,
        session=session,
        lines=[{"description": "Fee", "quantity": "1", "unit_amount": "1000.00"}],
    )
    issue_invoice(actor=accountant, invoice=invoice)
    p1 = record_payment(
        actor=accountant,
        institution=institution,
        student=student,
        campus=campus,
        amount="1000.00",
        idempotency_key="idem-1",
        allocations=[{"invoice": invoice, "amount": "1000.00"}],
    )
    p2 = record_payment(
        actor=accountant,
        institution=institution,
        student=student,
        campus=campus,
        amount="1000.00",
        idempotency_key="idem-1",
        allocations=[{"invoice": invoice, "amount": "1000.00"}],
    )
    assert p1.id == p2.id
    assert Payment.objects.filter(institution=institution, idempotency_key="idem-1").count() == 1


@pytest.mark.django_db
def test_adjustment_requires_approval_before_apply(
    api_client, accountant, principal, institution, campus, student, session
):
    invoice = create_invoice(
        actor=accountant,
        institution=institution,
        campus=campus,
        student=student,
        session=session,
        lines=[{"description": "Fee", "quantity": "1", "unit_amount": "5000.00"}],
    )
    issue_invoice(actor=accountant, invoice=invoice)
    api_client.force_authenticate(accountant)
    resp = api_client.post(
        "/api/v1/finance/adjustments/",
        {
            "institution": str(institution.id),
            "campus": str(campus.id),
            "invoice": str(invoice.id),
            "adjustment_type": "waiver",
            "amount": "1000.00",
            "currency": "NGN",
            "reason": "Policy waiver",
        },
        format="json",
    )
    assert resp.status_code == 201
    adjustment_id = resp.data["id"]

    apply_resp = api_client.post(
        f"/api/v1/finance/adjustments/{adjustment_id}/apply/", {}, format="json"
    )
    assert apply_resp.status_code == 409

    api_client.force_authenticate(principal)
    approve_resp = api_client.post(
        f"/api/v1/finance/adjustments/{adjustment_id}/approve/", {}, format="json"
    )
    assert approve_resp.status_code == 200
    adjustment = FinancialAdjustment.objects.get(id=adjustment_id)
    assert adjustment.status == FinancialAdjustment.Status.APPROVED


@pytest.mark.django_db
def test_finance_cross_institution_idor_returns_404(api_client, accountant, session):
    other = Institution.objects.create(name="Other", code="OTH")
    other_campus = Campus.objects.create(institution=other, name="Other", code="OC")
    other_student = Student.objects.create(
        institution=other,
        campus=other_campus,
        admission_number="ADM-OTH-1",
        first_name="Other",
        last_name="Student",
        date_of_birth=__import__("datetime").date(2012, 1, 1),
        admission_date=__import__("datetime").date(2026, 9, 1),
        status=Student.LifecycleStatus.ENROLLED,
    )
    other_category = FeeCategory.objects.create(institution=other, code="OTHF", name="Other Fee")
    other_invoice = create_invoice(
        actor=get_user_model().objects.create_superuser("root@x.test", "Passw0rd!123"),
        institution=other,
        campus=other_campus,
        student=other_student,
        session=AcademicSession.objects.create(
            institution=other, name="2026/2027", start_date="2026-09-01", end_date="2027-07-31"
        ),
        lines=[
            {
                "description": "Fee",
                "quantity": "1",
                "unit_amount": "100.00",
                "category": other_category,
            }
        ],
    )
    api_client.force_authenticate(accountant)
    resp = api_client.get(f"/api/v1/finance/invoices/{other_invoice.id}/")
    assert resp.status_code == 404


def _webhook_signature(secret: str, payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@override_settings(PAYMENT_WEBHOOK_SECRETS={"mock": "test-secret"})
@pytest.mark.django_db
def test_mock_webhook_verifies_payment_and_is_idempotent(
    api_client, institution, campus, student, accountant, session
):
    invoice = create_invoice(
        actor=accountant,
        institution=institution,
        campus=campus,
        student=student,
        session=session,
        lines=[{"description": "Fee", "quantity": "1", "unit_amount": "1000.00"}],
    )
    issue_invoice(actor=accountant, invoice=invoice)
    payment = record_payment(
        actor=accountant,
        institution=institution,
        student=student,
        campus=campus,
        amount="1000.00",
        provider="mock",
        provider_ref="mock-ref-1",
        idempotency_key="idem-webhook-1",
        allocations=[{"invoice": invoice, "amount": "1000.00"}],
    )
    payment.status = Payment.Status.PENDING
    payment.verified_at = None
    payment.save(update_fields=["status", "verified_at", "updated_at"])

    payload = {
        "event_id": "evt-1",
        "provider_ref": "mock-ref-1",
        "amount": "1000.00",
        "currency": "NGN",
        "status": "verified",
    }
    signature = _webhook_signature("test-secret", payload)
    resp1 = api_client.post(
        "/api/v1/finance/webhooks/payments/mock/",
        data=json.dumps(payload, separators=(",", ":"), sort_keys=True),
        content_type="application/json",
        HTTP_X_WEBHOOK_SIGNATURE=signature,
    )
    resp2 = api_client.post(
        "/api/v1/finance/webhooks/payments/mock/",
        data=json.dumps(payload, separators=(",", ":"), sort_keys=True),
        content_type="application/json",
        HTTP_X_WEBHOOK_SIGNATURE=signature,
    )

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    payment.refresh_from_db()
    invoice.refresh_from_db()
    assert payment.status == Payment.Status.VERIFIED
    assert invoice.status == Invoice.Status.PAID
    assert PaymentWebhookEvent.objects.filter(provider="mock", event_id="evt-1").count() == 1


@override_settings(PAYMENT_WEBHOOK_SECRETS={"mock": "test-secret"})
@pytest.mark.django_db
def test_mock_webhook_rejects_invalid_signature(api_client):
    payload = {"event_id": "evt-bad", "provider_ref": "x", "amount": "1.00", "currency": "NGN"}
    resp = api_client.post(
        "/api/v1/finance/webhooks/payments/mock/",
        data=json.dumps(payload, separators=(",", ":"), sort_keys=True),
        content_type="application/json",
        HTTP_X_WEBHOOK_SIGNATURE="bad",
    )
    assert resp.status_code == 400
    event = PaymentWebhookEvent.objects.get(provider="mock", event_id="evt-bad")
    assert event.status == PaymentWebhookEvent.Status.FAILED
    assert event.processing_detail == "invalid_signature"


@override_settings(PAYMENT_WEBHOOK_SECRETS={"mock": "test-secret"})
@pytest.mark.django_db
def test_mock_webhook_amount_mismatch_is_rejected(
    api_client, institution, campus, student, accountant, session
):
    invoice = create_invoice(
        actor=accountant,
        institution=institution,
        campus=campus,
        student=student,
        session=session,
        lines=[{"description": "Fee", "quantity": "1", "unit_amount": "1000.00"}],
    )
    issue_invoice(actor=accountant, invoice=invoice)
    record_payment(
        actor=accountant,
        institution=institution,
        student=student,
        campus=campus,
        amount="1000.00",
        provider="mock",
        provider_ref="mock-ref-mismatch",
        allocations=[{"invoice": invoice, "amount": "1000.00"}],
    )
    payload = {
        "event_id": "evt-mismatch",
        "provider_ref": "mock-ref-mismatch",
        "amount": "999.00",
        "currency": "NGN",
    }
    signature = _webhook_signature("test-secret", payload)
    resp = api_client.post(
        "/api/v1/finance/webhooks/payments/mock/",
        data=json.dumps(payload, separators=(",", ":"), sort_keys=True),
        content_type="application/json",
        HTTP_X_WEBHOOK_SIGNATURE=signature,
    )
    assert resp.status_code == 400
    event = PaymentWebhookEvent.objects.get(provider="mock", event_id="evt-mismatch")
    assert event.processing_detail == "amount_or_currency_mismatch"
