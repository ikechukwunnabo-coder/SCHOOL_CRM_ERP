from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_event
from apps.core.identifiers import generate_identifier

from .models import (
    FeeCategory,
    FeeSchedule,
    FinancialAdjustment,
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
)


class FinanceError(ValueError):
    pass


def ensure_institution_scope(actor, obj) -> None:
    if actor is None or getattr(actor, "is_superuser", False):
        return
    obj_institution_id = getattr(obj, "institution_id", None)
    model_label = getattr(getattr(obj, "_meta", None), "label", "").lower()
    if obj_institution_id is None and model_label == "institutions.institution":
        obj_institution_id = obj.pk
    if obj_institution_id != getattr(actor, "institution_id", None):
        raise FinanceError("institution_scope_violation")
    campus_id = getattr(obj, "campus_id", None)
    actor_campus_id = getattr(actor, "campus_id", None)
    if campus_id is not None and actor_campus_id not in (None, campus_id):
        raise FinanceError("campus_scope_violation")


def _recalculate_invoice(invoice: Invoice) -> Invoice:
    total = sum((line.line_total for line in invoice.lines.all()), Decimal("0.00"))
    allocated = sum(
        (allocation.amount for allocation in invoice.allocations.select_related("payment")),
        Decimal("0.00"),
    )
    if any(a.payment.status == Payment.Status.REVERSED for a in invoice.allocations.all()):
        allocated = Decimal("0.00")
    invoice.total_amount = total
    invoice.balance_amount = max(total - allocated, Decimal("0.00"))
    if invoice.status != Invoice.Status.VOIDED:
        if total > 0 and invoice.balance_amount == 0:
            invoice.status = Invoice.Status.PAID
        elif allocated > 0:
            invoice.status = Invoice.Status.PARTIALLY_PAID
        elif invoice.status != Invoice.Status.DRAFT:
            invoice.status = Invoice.Status.ISSUED
    invoice.save(update_fields=["total_amount", "balance_amount", "status", "updated_at"])
    return invoice


@transaction.atomic
def create_invoice(
    *,
    actor,
    institution,
    student,
    campus=None,
    session=None,
    term=None,
    due_date=None,
    notes="",
    lines,
):
    ensure_institution_scope(actor, institution)
    ensure_institution_scope(actor, student)
    if campus is not None:
        ensure_institution_scope(actor, campus)
    if lines is None or len(lines) == 0:
        raise FinanceError("invoice_lines_required")
    currency = institution.settings.get("currency", "NGN") if institution.settings else "NGN"
    invoice = Invoice.objects.create(
        institution=institution,
        campus=campus or student.campus,
        student=student,
        session=session,
        term=term,
        invoice_number=generate_identifier(
            institution, "invoice_number", year=timezone.now().year
        ),
        currency=currency,
        due_date=due_date,
        notes=notes,
        created_by=actor,
    )
    for item in lines:
        quantity = Decimal(str(item.get("quantity", "1")))
        unit_amount = Decimal(str(item.get("unit_amount", "0")))
        line_total = quantity * unit_amount
        category = item.get("category")
        fee_schedule = item.get("fee_schedule")
        if isinstance(category, str):
            category = FeeCategory.objects.get(pk=category)
        if isinstance(fee_schedule, str):
            fee_schedule = FeeSchedule.objects.get(pk=fee_schedule)
        if category is not None:
            ensure_institution_scope(actor, category)
        if fee_schedule is not None:
            ensure_institution_scope(actor, fee_schedule)
        InvoiceLine.objects.create(
            invoice=invoice,
            fee_schedule=fee_schedule,
            category=category,
            description=item.get("description", ""),
            quantity=quantity,
            unit_amount=unit_amount,
            line_total=line_total,
        )
    _recalculate_invoice(invoice)
    log_event(
        "finance.invoice_created",
        actor=actor,
        target_type="finance.Invoice",
        target_id=invoice.pk,
        institution_id=invoice.institution_id,
        campus_id=invoice.campus_id,
        metadata={"invoice_number": invoice.invoice_number, "total": str(invoice.total_amount)},
    )
    return invoice


@transaction.atomic
def issue_invoice(*, actor, invoice: Invoice) -> Invoice:
    ensure_institution_scope(actor, invoice)
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status != Invoice.Status.DRAFT:
        raise FinanceError("invoice_not_draft")
    if invoice.total_amount <= 0:
        raise FinanceError("invoice_total_invalid")
    invoice.status = Invoice.Status.ISSUED
    invoice.issued_at = timezone.now()
    invoice.save(update_fields=["status", "issued_at", "updated_at"])
    log_event(
        "finance.invoice_issued",
        actor=actor,
        target_type="finance.Invoice",
        target_id=invoice.pk,
        institution_id=invoice.institution_id,
        campus_id=invoice.campus_id,
        metadata={"invoice_number": invoice.invoice_number},
    )
    return invoice


@transaction.atomic
def record_payment(
    *,
    actor,
    institution,
    student=None,
    campus=None,
    amount,
    currency="NGN",
    method="manual",
    provider="",
    provider_ref="",
    idempotency_key="",
    notes="",
    allocations=None,
) -> Payment:
    ensure_institution_scope(actor, institution)
    if student is not None:
        ensure_institution_scope(actor, student)
    if campus is not None:
        ensure_institution_scope(actor, campus)
    amount = Decimal(str(amount))
    if amount <= 0:
        raise FinanceError("payment_amount_invalid")
    if idempotency_key:
        existing = Payment.objects.filter(
            institution=institution, idempotency_key=idempotency_key
        ).first()
        if existing:
            return existing

    payment = Payment.objects.create(
        institution=institution,
        campus=campus or (student.campus if student else None),
        student=student,
        receipt_number=generate_identifier(
            institution, "receipt_number", year=timezone.now().year
        ),
        amount=amount,
        currency=currency,
        method=method,
        provider=provider,
        provider_ref=provider_ref,
        idempotency_key=idempotency_key,
        received_at=timezone.now(),
        verified_at=timezone.now(),
        status=Payment.Status.VERIFIED,
        posted_by=actor,
        notes=notes,
    )
    remaining = amount
    for allocation in allocations or []:
        if remaining <= 0:
            break
        invoice = allocation["invoice"]
        if isinstance(invoice, str):
            invoice = Invoice.objects.select_for_update().get(pk=invoice)
        else:
            invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        ensure_institution_scope(actor, invoice)
        if invoice.status not in {
            Invoice.Status.ISSUED,
            Invoice.Status.PARTIALLY_PAID,
            Invoice.Status.PAID,
        }:
            raise FinanceError("invoice_not_payable")
        alloc_amount = Decimal(str(allocation.get("amount", invoice.balance_amount)))
        alloc_amount = min(alloc_amount, remaining, invoice.balance_amount)
        if alloc_amount <= 0:
            continue
        PaymentAllocation.objects.create(
            payment=payment,
            invoice=invoice,
            amount=alloc_amount,
            allocated_by=actor,
        )
        remaining -= alloc_amount
        _recalculate_invoice(invoice)

    log_event(
        "finance.payment_recorded",
        actor=actor,
        target_type="finance.Payment",
        target_id=payment.pk,
        institution_id=payment.institution_id,
        campus_id=payment.campus_id,
        metadata={
            "receipt_number": payment.receipt_number,
            "amount": str(payment.amount),
            "idempotency_key": payment.idempotency_key,
        },
    )
    return payment


@transaction.atomic
def request_adjustment(
    *,
    actor,
    institution,
    adjustment_type,
    amount,
    reason,
    currency="NGN",
    invoice=None,
    payment=None,
    campus=None,
) -> FinancialAdjustment:
    ensure_institution_scope(actor, institution)
    if not reason or not reason.strip():
        raise FinanceError("adjustment_reason_required")
    amount = Decimal(str(amount))
    if amount <= 0:
        raise FinanceError("adjustment_amount_invalid")
    if invoice is not None:
        ensure_institution_scope(actor, invoice)
    if payment is not None:
        ensure_institution_scope(actor, payment)
    adjustment = FinancialAdjustment.objects.create(
        institution=institution,
        campus=campus or (invoice.campus if invoice else payment.campus if payment else None),
        invoice=invoice,
        payment=payment,
        adjustment_type=adjustment_type,
        amount=amount,
        currency=currency,
        reason=reason.strip(),
        requested_by=actor,
    )
    log_event(
        "finance.adjustment_requested",
        actor=actor,
        target_type="finance.FinancialAdjustment",
        target_id=adjustment.pk,
        institution_id=adjustment.institution_id,
        campus_id=adjustment.campus_id,
        reason=adjustment.reason,
        metadata={"type": adjustment.adjustment_type, "amount": str(adjustment.amount)},
    )
    return adjustment


@transaction.atomic
def approve_adjustment(*, actor, adjustment: FinancialAdjustment) -> FinancialAdjustment:
    ensure_institution_scope(actor, adjustment)
    adjustment = FinancialAdjustment.objects.select_for_update().get(pk=adjustment.pk)
    if adjustment.status != FinancialAdjustment.Status.PENDING:
        raise FinanceError("adjustment_not_pending")
    adjustment.status = FinancialAdjustment.Status.APPROVED
    adjustment.approved_by = actor
    adjustment.save(update_fields=["status", "approved_by", "updated_at"])
    log_event(
        "finance.adjustment_approved",
        actor=actor,
        target_type="finance.FinancialAdjustment",
        target_id=adjustment.pk,
        institution_id=adjustment.institution_id,
        campus_id=adjustment.campus_id,
        reason=adjustment.reason,
    )
    return adjustment


@transaction.atomic
def apply_adjustment(*, actor, adjustment: FinancialAdjustment) -> FinancialAdjustment:
    ensure_institution_scope(actor, adjustment)
    adjustment = FinancialAdjustment.objects.select_for_update().get(pk=adjustment.pk)
    if adjustment.status != FinancialAdjustment.Status.APPROVED:
        raise FinanceError("adjustment_not_approved")

    if adjustment.adjustment_type in {
        FinancialAdjustment.Type.REVERSAL,
        FinancialAdjustment.Type.REFUND,
    } and adjustment.payment_id:
        payment = Payment.objects.select_for_update().get(pk=adjustment.payment_id)
        payment.status = (
            Payment.Status.REFUNDED
            if adjustment.adjustment_type == FinancialAdjustment.Type.REFUND
            else Payment.Status.REVERSED
        )
        payment.save(update_fields=["status", "updated_at"])
        for alloc in payment.allocations.select_for_update().select_related("invoice"):
            if alloc.invoice.status != Invoice.Status.VOIDED:
                alloc.invoice.status = Invoice.Status.ISSUED
                alloc.invoice.save(update_fields=["status", "updated_at"])
                _recalculate_invoice(alloc.invoice)

    if adjustment.adjustment_type in {
        FinancialAdjustment.Type.WAIVER,
        FinancialAdjustment.Type.CREDIT,
    } and adjustment.invoice_id:
        invoice = Invoice.objects.select_for_update().get(pk=adjustment.invoice_id)
        invoice.balance_amount = max(invoice.balance_amount - adjustment.amount, Decimal("0.00"))
        if invoice.balance_amount == 0 and invoice.total_amount > 0:
            invoice.status = Invoice.Status.PAID
        elif invoice.status == Invoice.Status.DRAFT:
            pass
        else:
            invoice.status = Invoice.Status.PARTIALLY_PAID
        invoice.save(update_fields=["balance_amount", "status", "updated_at"])

    adjustment.status = FinancialAdjustment.Status.APPLIED
    adjustment.applied_by = actor
    adjustment.applied_at = timezone.now()
    adjustment.save(update_fields=["status", "applied_by", "applied_at", "updated_at"])
    log_event(
        "finance.adjustment_applied",
        actor=actor,
        target_type="finance.FinancialAdjustment",
        target_id=adjustment.pk,
        institution_id=adjustment.institution_id,
        campus_id=adjustment.campus_id,
        reason=adjustment.reason,
        metadata={"type": adjustment.adjustment_type, "amount": str(adjustment.amount)},
    )
    return adjustment
