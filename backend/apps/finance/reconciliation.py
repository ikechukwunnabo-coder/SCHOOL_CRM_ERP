from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_event

from .models import Payment, ReconciliationRecord
from .services import FinanceError, ensure_institution_scope


@transaction.atomic
def import_reconciliation_row(
    *,
    actor,
    institution,
    provider,
    reference,
    amount,
    currency="NGN",
    status=ReconciliationRecord.Status.PENDING,
    source="manual",
    payload=None,
    campus=None,
):
    ensure_institution_scope(actor, institution)
    if campus is not None:
        ensure_institution_scope(actor, campus)
    valid_statuses = {choice for choice, _ in ReconciliationRecord.Status.choices}
    if status not in valid_statuses:
        raise FinanceError("invalid_reconciliation_status")
    record, created = ReconciliationRecord.objects.select_for_update().get_or_create(
        institution=institution,
        provider=provider,
        reference=reference,
        defaults={
            "campus": campus,
            "amount": Decimal(str(amount)),
            "currency": currency,
            "status": status,
            "source": source,
            "payload": payload or {},
        },
    )
    if not created:
        record.payload = payload or record.payload
        record.status = status or record.status
        record.amount = Decimal(str(amount))
        record.currency = currency
        record.campus = campus or record.campus
        record.save(
            update_fields=["payload", "status", "amount", "currency", "campus", "updated_at"]
        )
    log_event(
        "finance.reconciliation_imported",
        actor=actor,
        target_type="finance.ReconciliationRecord",
        target_id=record.pk,
        institution_id=record.institution_id,
        campus_id=record.campus_id,
        metadata={"provider": provider, "reference": reference, "created": created},
    )
    return record, created


@transaction.atomic
def reconcile_record(*, actor, record: ReconciliationRecord):
    ensure_institution_scope(actor, record)
    record = ReconciliationRecord.objects.select_for_update().get(pk=record.pk)
    payment = (
        Payment.objects.select_for_update()
        .filter(
            institution_id=record.institution_id,
            provider=record.provider,
            provider_ref=record.reference,
            status=Payment.Status.VERIFIED,
        )
        .first()
    )
    if payment is None:
        record.status = ReconciliationRecord.Status.MISSING
        record.payment = None
        record.exception_reason = "verified_payment_not_found"
        record.reconciled_at = timezone.now()
        record.save(
            update_fields=[
                "status",
                "payment",
                "exception_reason",
                "reconciled_at",
                "updated_at",
            ]
        )
        log_event(
            "finance.reconciliation_exception",
            actor=actor,
            target_type="finance.ReconciliationRecord",
            target_id=record.pk,
            institution_id=record.institution_id,
            campus_id=record.campus_id,
            metadata={"status": record.status, "reason": record.exception_reason},
        )
        return record
    if payment.amount != record.amount or payment.currency != record.currency:
        record.status = ReconciliationRecord.Status.MISMATCHED
        record.payment = payment
        record.exception_reason = "amount_or_currency_mismatch"
        record.reconciled_at = timezone.now()
        record.save(
            update_fields=[
                "status",
                "payment",
                "exception_reason",
                "reconciled_at",
                "updated_at",
            ]
        )
        log_event(
            "finance.reconciliation_exception",
            actor=actor,
            target_type="finance.ReconciliationRecord",
            target_id=record.pk,
            institution_id=record.institution_id,
            campus_id=record.campus_id,
            metadata={
                "status": record.status,
                "reason": record.exception_reason,
                "payment_id": str(payment.id),
            },
        )
        return record
    record.status = ReconciliationRecord.Status.MATCHED
    record.payment = payment
    record.exception_reason = ""
    record.reconciled_at = timezone.now()
    record.save(
        update_fields=[
            "status",
            "payment",
            "exception_reason",
            "reconciled_at",
            "updated_at",
        ]
    )
    log_event(
        "finance.reconciliation_matched",
        actor=actor,
        target_type="finance.ReconciliationRecord",
        target_id=record.pk,
        institution_id=record.institution_id,
        campus_id=record.campus_id,
        metadata={"payment_id": str(payment.id), "provider": record.provider},
    )
    return record
