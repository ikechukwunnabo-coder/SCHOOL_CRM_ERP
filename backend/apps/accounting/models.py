from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class LedgerAccount(TimeStampedModel):
    class Type(models.TextChoices):
        ASSET = "asset", "Asset"
        LIABILITY = "liability", "Liability"
        EQUITY = "equity", "Equity"
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    institution = models.ForeignKey(
        "institutions.Institution", on_delete=models.PROTECT, related_name="ledger_accounts"
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    account_type = models.CharField(max_length=20, choices=Type.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["institution", "code"], name="uq_ledger_account_code")
        ]


class JournalEntry(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"

    institution = models.ForeignKey(
        "institutions.Institution", on_delete=models.PROTECT, related_name="journal_entries"
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="journal_entries",
    )
    reference = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    entry_date = models.DateField()
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="posted_journal_entries",
    )
    source_type = models.CharField(max_length=60, blank=True)
    source_id = models.CharField(max_length=64, blank=True)
    idempotency_key = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-entry_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="uq_journal_entry_idempotency",
            )
        ]


class JournalLine(TimeStampedModel):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(
        LedgerAccount, on_delete=models.PROTECT, related_name="journal_lines"
    )
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    memo = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(debit__gte=Decimal("0.00")) & Q(credit__gte=Decimal("0.00")),
                name="ck_journal_line_non_negative",
            ),
            models.CheckConstraint(
                condition=~(Q(debit__gt=Decimal("0.00")) & Q(credit__gt=Decimal("0.00"))),
                name="ck_journal_line_single_side",
            ),
            models.UniqueConstraint(
                fields=["entry", "account"], name="uq_journal_line_entry_account"
            ),
        ]
