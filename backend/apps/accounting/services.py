from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_event

from .models import JournalEntry, JournalLine, LedgerAccount


class AccountingError(ValueError):
    pass


def _ensure_scope(actor, obj) -> None:
    if actor is None or getattr(actor, "is_superuser", False) or obj is None:
        return
    obj_institution_id = getattr(obj, "institution_id", None)
    model_label = getattr(getattr(obj, "_meta", None), "label", "").lower()
    if obj_institution_id is None and model_label == "institutions.institution":
        obj_institution_id = obj.pk
    if obj_institution_id != getattr(actor, "institution_id", None):
        raise AccountingError("institution_scope_violation")
    campus_id = getattr(obj, "campus_id", None)
    actor_campus_id = getattr(actor, "campus_id", None)
    if campus_id is not None and actor_campus_id not in (None, campus_id):
        raise AccountingError("campus_scope_violation")


def _normalize_amount(value, field: str) -> Decimal:
    amount = Decimal(str(value or "0"))
    if amount < Decimal("0.00"):
        raise AccountingError(f"{field}_negative")
    return amount


def _resolve_lines(*, actor, institution, lines) -> list[dict]:
    if not lines:
        raise AccountingError("journal_requires_lines")
    normalized: list[dict] = []
    seen_accounts: set[str] = set()
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")
    for line in lines:
        account = line.get("account")
        if isinstance(account, str):
            try:
                account = LedgerAccount.objects.get(pk=account)
            except LedgerAccount.DoesNotExist as exc:
                raise AccountingError("account_not_found") from exc
        if not isinstance(account, LedgerAccount):
            raise AccountingError("account_required")
        _ensure_scope(actor, account)
        if account.institution_id != institution.id:
            raise AccountingError("account_institution_mismatch")
        if not account.is_active:
            raise AccountingError("account_inactive")
        account_key = str(account.pk)
        if account_key in seen_accounts:
            raise AccountingError("duplicate_journal_account")
        seen_accounts.add(account_key)
        debit = _normalize_amount(line.get("debit", "0"), "debit")
        credit = _normalize_amount(line.get("credit", "0"), "credit")
        if debit > Decimal("0.00") and credit > Decimal("0.00"):
            raise AccountingError("journal_line_double_sided")
        if debit == Decimal("0.00") and credit == Decimal("0.00"):
            raise AccountingError("journal_line_empty")
        total_debit += debit
        total_credit += credit
        normalized.append(
            {
                "account": account,
                "debit": debit,
                "credit": credit,
                "memo": str(line.get("memo", ""))[:255],
            }
        )
    if total_debit != total_credit:
        raise AccountingError("journal_not_balanced")
    return normalized


def _existing_entry(*, institution, idempotency_key):
    if not idempotency_key:
        return None
    return (
        JournalEntry.objects.select_for_update()
        .filter(institution=institution, idempotency_key=idempotency_key)
        .first()
    )


def _create_entry(
    *,
    actor,
    institution,
    entry_date,
    lines,
    description,
    reference,
    campus,
    source_type,
    source_id,
    idempotency_key,
    status,
):
    _ensure_scope(actor, institution)
    _ensure_scope(actor, campus)
    normalized_lines = _resolve_lines(actor=actor, institution=institution, lines=lines)
    entry = JournalEntry.objects.create(
        institution=institution,
        campus=campus,
        reference=str(reference or "")[:120],
        description=description or "",
        entry_date=entry_date,
        posted_by=actor,
        source_type=str(source_type or "")[:60],
        source_id=str(source_id or "")[:64],
        idempotency_key=str(idempotency_key or "")[:120],
        status=status,
        posted_at=timezone.now() if status == JournalEntry.Status.POSTED else None,
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                entry=entry,
                account=line["account"],
                debit=line["debit"],
                credit=line["credit"],
                memo=line["memo"],
            )
            for line in normalized_lines
        ]
    )
    return entry


@transaction.atomic
def create_journal_entry(
    *,
    actor,
    institution,
    entry_date,
    lines,
    description="",
    reference="",
    campus=None,
    source_type="",
    source_id="",
    idempotency_key="",
):
    existing = _existing_entry(institution=institution, idempotency_key=idempotency_key)
    if existing:
        return existing, False
    entry = _create_entry(
        actor=actor,
        institution=institution,
        entry_date=entry_date,
        lines=lines,
        description=description,
        reference=reference,
        campus=campus,
        source_type=source_type,
        source_id=source_id,
        idempotency_key=idempotency_key,
        status=JournalEntry.Status.DRAFT,
    )
    log_event(
        "accounting.journal_created",
        actor=actor,
        target_type="accounting.JournalEntry",
        target_id=entry.pk,
        institution_id=institution.id,
        campus_id=getattr(campus, "id", None),
        metadata={"reference": reference, "source_type": source_type},
    )
    return entry, True


@transaction.atomic
def post_journal_entry(
    *,
    actor,
    institution,
    entry_date,
    lines,
    description="",
    reference="",
    campus=None,
    source_type="",
    source_id="",
    idempotency_key="",
):
    existing = _existing_entry(institution=institution, idempotency_key=idempotency_key)
    if existing:
        return existing, False
    entry = _create_entry(
        actor=actor,
        institution=institution,
        entry_date=entry_date,
        lines=lines,
        description=description,
        reference=reference,
        campus=campus,
        source_type=source_type,
        source_id=source_id,
        idempotency_key=idempotency_key,
        status=JournalEntry.Status.POSTED,
    )
    log_event(
        "accounting.journal_posted",
        actor=actor,
        target_type="accounting.JournalEntry",
        target_id=entry.pk,
        institution_id=institution.id,
        campus_id=getattr(campus, "id", None),
        metadata={
            "reference": reference,
            "source_type": source_type,
            "source_id": str(source_id or ""),
        },
    )
    return entry, True


@transaction.atomic
def approve_journal_entry(*, actor, entry: JournalEntry):
    _ensure_scope(actor, entry)
    entry = JournalEntry.objects.select_for_update().get(pk=entry.pk)
    if entry.status == JournalEntry.Status.POSTED:
        return entry
    if entry.status != JournalEntry.Status.DRAFT:
        raise AccountingError("journal_not_approvable")
    _resolve_lines(
        actor=actor,
        institution=entry.institution,
        lines=[
            {
                "account": line.account,
                "debit": line.debit,
                "credit": line.credit,
                "memo": line.memo,
            }
            for line in entry.lines.select_related("account")
        ],
    )
    entry.status = JournalEntry.Status.POSTED
    entry.posted_at = timezone.now()
    entry.save(update_fields=["status", "posted_at", "updated_at"])
    log_event(
        "accounting.journal_posted",
        actor=actor,
        target_type="accounting.JournalEntry",
        target_id=entry.pk,
        institution_id=entry.institution_id,
        campus_id=entry.campus_id,
        metadata={"reference": entry.reference, "source_type": entry.source_type},
    )
    return entry
