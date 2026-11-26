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
from apps.guardians.models import Guardian
from apps.institutions.models import Campus, Institution
from apps.permissions.models import Permission, Role, RolePermission, UserRole
from apps.students.models import Student, StudentGuardian


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


@pytest.mark.django_db
def test_parent_portal_sees_only_linked_student_finance(
    api_client, institution, campus, session, student, accountant
):
    other_student = Student.objects.create(
        institution=institution,
        campus=campus,
        admission_number="ADM-FIN-002",
        first_name="Bola",
        last_name="Okafor",
        date_of_birth=__import__("datetime").date(2011, 2, 2),
        admission_date=__import__("datetime").date(2026, 9, 1),
        status=Student.LifecycleStatus.ENROLLED,
    )
    inv1 = create_invoice(
        actor=accountant,
        institution=institution,
        campus=campus,
        student=student,
        session=session,
        lines=[{"description": "Fee", "quantity": "1", "unit_amount": "1000.00"}],
    )
    inv2 = create_invoice(
        actor=accountant,
        institution=institution,
        campus=campus,
        student=other_student,
        session=session,
        lines=[{"description": "Fee", "quantity": "1", "unit_amount": "2000.00"}],
    )
    issue_invoice(actor=accountant, invoice=inv1)
    issue_invoice(actor=accountant, invoice=inv2)

    parent_user = get_user_model().objects.create_user(
        email="parent@fin.test", password="Passw0rd!123", institution=institution, campus=campus
    )
    guardian = Guardian.objects.create(
        institution=institution,
        user=parent_user,
        first_name="Parent",
        last_name="User",
        phone="08000000000",
        email="parent@fin.test",
    )
    StudentGuardian.objects.create(
        student=student,
        guardian=guardian,
        relationship="Mother",
        is_primary=True,
        portal_access=True,
    )
    role, _ = Role.objects.get_or_create(
        name="Parent/Guardian", defaults={"is_system": True, "institution": institution}
    )
    UserRole.objects.get_or_create(
        user=parent_user,
        role=role,
        scope_type=UserRole.ScopeType.OWN,
        defaults={"is_active": True},
    )
    for perm in Permission.objects.filter(module="finance", verb__in=["view", "print"]):
        RolePermission.objects.get_or_create(role=role, permission=perm)

    api_client.force_authenticate(parent_user)
    list_resp = api_client.get("/api/v1/finance/invoices/")
    assert list_resp.status_code == 200
    ids = {item["id"] for item in list_resp.data["results"]}
    assert str(inv1.id) in ids
    assert str(inv2.id) not in ids

    detail_resp = api_client.get(f"/api/v1/finance/invoices/{inv2.id}/")
    assert detail_resp.status_code == 404

    create_resp = api_client.post(
        "/api/v1/finance/payments/",
        {
            "institution": str(institution.id),
            "student": str(student.id),
            "amount": "100.00",
        },
        format="json",
    )
    assert create_resp.status_code == 403


@override_settings(
    PAYMENT_WEBHOOK_SECRETS={"flutterwave": "flw-hash"},
    PAYMENT_FLUTTERWAVE_SECRET_KEY="flw-secret",
    PAYMENT_FLUTTERWAVE_BASE_URL="https://api.flutterwave.test/v3",
)
@pytest.mark.django_db
def test_flutterwave_webhook_verifies_and_is_idempotent(
    api_client, institution, campus, student, accountant, session, monkeypatch
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
        provider="flutterwave",
        provider_ref="tx-ref-1",
        allocations=[{"invoice": invoice, "amount": "1000.00"}],
    )
    payment.status = Payment.Status.PENDING
    payment.verified_at = None
    payment.save(update_fields=["status", "verified_at", "updated_at"])

    class FakeResp:
        def read(self):
            return json.dumps(
                {
                    "status": "success",
                    "data": {
                        "status": "successful",
                        "tx_ref": "tx-ref-1",
                        "amount": 1000.0,
                        "currency": "NGN",
                    },
                }
            ).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=10: FakeResp())

    payload = {
        "event_id": "flw-evt-1",
        "provider_ref": "tx-ref-1",
        "amount": "1000.00",
        "currency": "NGN",
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    resp1 = api_client.post(
        "/api/v1/finance/webhooks/payments/flutterwave/",
        data=body,
        content_type="application/json",
        HTTP_VERIF_HASH="flw-hash",
    )
    resp2 = api_client.post(
        "/api/v1/finance/webhooks/payments/flutterwave/",
        data=body,
        content_type="application/json",
        HTTP_VERIF_HASH="flw-hash",
    )
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    payment.refresh_from_db()
    invoice.refresh_from_db()
    assert payment.status == Payment.Status.VERIFIED
    assert invoice.status == Invoice.Status.PAID
    assert (
        PaymentWebhookEvent.objects.filter(provider="flutterwave", event_id="flw-evt-1").count()
        == 1
    )


@override_settings(PAYMENT_WEBHOOK_SECRETS={"flutterwave": "flw-hash"})
@pytest.mark.django_db
def test_flutterwave_webhook_rejects_invalid_signature(api_client):
    payload = {"event_id": "flw-bad", "provider_ref": "x", "amount": "1.00", "currency": "NGN"}
    resp = api_client.post(
        "/api/v1/finance/webhooks/payments/flutterwave/",
        data=json.dumps(payload, separators=(",", ":"), sort_keys=True),
        content_type="application/json",
        HTTP_VERIF_HASH="wrong",
    )
    assert resp.status_code == 400
    event = PaymentWebhookEvent.objects.get(provider="flutterwave", event_id="flw-bad")
    assert event.processing_detail == "invalid_signature"


@pytest.mark.django_db
def test_reconciliation_import_match_and_exception(
    accountant, institution, campus, session, student
):
    category = FeeCategory.objects.create(
        institution=institution, campus=campus, code="LAB", name="Lab"
    )
    invoice = create_invoice(
        actor=accountant,
        institution=institution,
        campus=campus,
        student=student,
        session=session,
        lines=[
            {
                "description": "Lab",
                "quantity": "1",
                "unit_amount": "5000.00",
                "category": category,
            }
        ],
    )
    issue_invoice(actor=accountant, invoice=invoice)
    payment = record_payment(
        actor=accountant,
        institution=institution,
        student=student,
        campus=campus,
        amount="5000.00",
        provider="mock",
        provider_ref="bank-ref-1",
        allocations=[{"invoice": invoice, "amount": "5000.00"}],
    )

    from apps.finance.reconciliation import import_reconciliation_row, reconcile_record

    record, _ = import_reconciliation_row(
        actor=accountant,
        institution=institution,
        provider="mock",
        reference="bank-ref-1",
        amount="5000.00",
        currency="NGN",
        campus=campus,
    )
    record = reconcile_record(actor=accountant, record=record)
    assert record.status == "matched"
    assert record.payment_id == payment.id

    bad, _ = import_reconciliation_row(
        actor=accountant,
        institution=institution,
        provider="mock",
        reference="missing-ref",
        amount="999.00",
        currency="NGN",
        campus=campus,
    )
    bad = reconcile_record(actor=accountant, record=bad)
    assert bad.status == "missing"
    assert bad.exception_reason


@pytest.mark.django_db
def test_finance_dashboard_returns_query_backed_summary(
    api_client, accountant, institution, campus, session, student
):
    category = FeeCategory.objects.create(
        institution=institution, campus=campus, code="DASH", name="Dash"
    )
    invoice = create_invoice(
        actor=accountant,
        institution=institution,
        campus=campus,
        student=student,
        session=session,
        lines=[
            {
                "description": "Dash",
                "quantity": "1",
                "unit_amount": "2000.00",
                "category": category,
            }
        ],
    )
    issue_invoice(actor=accountant, invoice=invoice)
    record_payment(
        actor=accountant,
        institution=institution,
        student=student,
        campus=campus,
        amount="2000.00",
        allocations=[{"invoice": invoice, "amount": "2000.00"}],
    )
    api_client.force_authenticate(accountant)
    resp = api_client.get("/api/v1/finance/dashboard/")
    assert resp.status_code == 200
    assert resp.data["invoices"]["count"] >= 1
    assert resp.data["payments"]["count"] >= 1


@pytest.mark.django_db
def test_reconciliation_exception_can_be_resolved(accountant, institution, campus):
    from apps.finance.reconciliation import (
        import_reconciliation_row,
        reconcile_record,
        resolve_reconciliation,
    )

    record, _ = import_reconciliation_row(
        actor=accountant,
        institution=institution,
        provider="mock",
        reference="resolve-me",
        amount="100.00",
        currency="NGN",
        campus=campus,
    )
    record = reconcile_record(actor=accountant, record=record)
    assert record.status == "missing"
    record = resolve_reconciliation(actor=accountant, record=record, reason="manual_adjustment")
    assert record.status == "resolved"
    assert record.exception_reason == "manual_adjustment"


@pytest.mark.django_db
def test_reconciliation_resolve_requires_update_permission(
    api_client, institution, campus
):
    from apps.finance.reconciliation import import_reconciliation_row, reconcile_record

    viewer = get_user_model().objects.create_user(
        email="viewer@fin.test", password="Passw0rd!123", institution=institution, campus=campus
    )
    grant_role(viewer, institution=institution, campus=campus, role_name="Registrar/Admissions")
    accountant = get_user_model().objects.create_user(
        email="acct2@fin.test", password="Passw0rd!123", institution=institution, campus=campus
    )
    grant_role(accountant, institution=institution, campus=campus, role_name="Bursar/Accountant")
    record, _ = import_reconciliation_row(
        actor=accountant,
        institution=institution,
        provider="mock",
        reference="no-resolve",
        amount="10.00",
        currency="NGN",
        campus=campus,
    )
    reconcile_record(actor=accountant, record=record)
    api_client.force_authenticate(viewer)
    resp = api_client.post(
        f"/api/v1/finance/reconciliation-records/{record.id}/resolve/",
        {"reason": "x"},
        format="json",
    )
    assert resp.status_code in {403, 404}


@pytest.mark.django_db
def test_finance_dashboard_denies_unauthenticated(api_client):
    resp = api_client.get("/api/v1/finance/dashboard/")
    assert resp.status_code in {401, 403}
@pytest.mark.django_db
def test_reconciliation_summary_denies_unauthenticated(api_client):
    resp = api_client.get("/api/v1/finance/reconciliation-records/summary/")
    assert resp.status_code in {401, 403}


@pytest.mark.django_db
def test_reconciliation_import_requires_create_permission(api_client, institution, campus):
    viewer = get_user_model().objects.create_user(
        email="viewer-import@fin.test",
        password="Passw0rd!123",
        institution=institution,
        campus=campus,
    )
    grant_role(viewer, institution=institution, campus=campus, role_name="Registrar/Admissions")
    api_client.force_authenticate(viewer)
    resp = api_client.post(
        "/api/v1/finance/reconciliation-records/import/",
        {"provider": "mock", "reference": "x", "amount": "1.00", "currency": "NGN"},
        format="json",
    )
    assert resp.status_code in {403, 404}
@pytest.mark.django_db
def test_finance_invoice_create_denies_parent(api_client, institution, campus, student):
    parent = get_user_model().objects.create_user(
        email="parent-create@fin.test",
        password="Passw0rd!123",
        institution=institution,
        campus=campus,
    )
    grant_role(parent, institution=institution, campus=campus, role_name="Parent/Guardian")
    guardian = Guardian.objects.create(
        institution=institution,
        first_name="P",
        last_name="X",
        phone="08000000001",
        user=parent,
    )
    StudentGuardian.objects.create(
        student=student,
        guardian=guardian,
        relationship="Parent",
        is_primary=True,
        portal_access=True,
    )
    category = FeeCategory.objects.create(institution=institution, name="TuitionX", code="TUX")
    api_client.force_authenticate(parent)
    resp = api_client.post(
        "/api/v1/finance/invoices/",
        {
            "student": str(student.id),
            "lines": [
                {
                    "description": "X",
                    "quantity": "1",
                    "unit_amount": "1.00",
                    "category": str(category.id),
                }
            ],
        },
        format="json",
    )
    assert resp.status_code in {403, 404}


@pytest.mark.django_db
def test_finance_payment_create_denies_parent(api_client, institution, campus, student):
    parent = get_user_model().objects.create_user(
        email="parent-pay@fin.test",
        password="Passw0rd!123",
        institution=institution,
        campus=campus,
    )
    grant_role(parent, institution=institution, campus=campus, role_name="Parent/Guardian")
    guardian = Guardian.objects.create(
        institution=institution,
        first_name="P",
        last_name="Y",
        phone="08000000002",
        user=parent,
    )
    StudentGuardian.objects.create(
        student=student,
        guardian=guardian,
        relationship="Parent",
        is_primary=True,
        portal_access=True,
    )
    api_client.force_authenticate(parent)
    resp = api_client.post(
        "/api/v1/finance/payments/",
        {"student": str(student.id), "amount": "1.00", "currency": "NGN"},
        format="json",
    )
    assert resp.status_code in {403, 404}


@pytest.mark.django_db
def test_reconciliation_reconcile_requires_update_permission(api_client, institution, campus):
    viewer = get_user_model().objects.create_user(
        email="viewer-recon@fin.test",
        password="Passw0rd!123",
        institution=institution,
        campus=campus,
    )
    grant_role(viewer, institution=institution, campus=campus, role_name="Registrar/Admissions")
    accountant = get_user_model().objects.create_user(
        email="acct-recon@fin.test",
        password="Passw0rd!123",
        institution=institution,
        campus=campus,
    )
    grant_role(accountant, institution=institution, campus=campus, role_name="Bursar/Accountant")
    from apps.finance.reconciliation import import_reconciliation_row

    record, _ = import_reconciliation_row(
        actor=accountant,
        institution=institution,
        provider="mock",
        reference="rbac-recon",
        amount="1.00",
        currency="NGN",
        campus=campus,
    )
    api_client.force_authenticate(viewer)
    resp = api_client.post(f"/api/v1/finance/reconciliation-records/{record.id}/reconcile/")
    assert resp.status_code in {403, 404}
