from __future__ import annotations

from django.db import transaction

from .models import IdentifierSequence

DEFAULT_PATTERNS = {
    "application_number": "APP-{YYYY}-{seq:06d}",
    "admission_number": "ADM-{YYYY}-{seq:06d}",
    "employee_number": "EMP-{YYYY}-{seq:05d}",
    "invoice_number": "INV-{YYYY}-{seq:06d}",
    "receipt_number": "RCT-{YYYY}-{seq:06d}",
    "transcript_reference": "TR-{institution_code}-{YYYY}-{seq:06d}",
}


class IdentifierError(ValueError):
    pass


def next_sequence_value(institution, kind: str, *, scope: str = "default") -> int:
    with transaction.atomic():
        row, _ = IdentifierSequence.objects.select_for_update().get_or_create(
            institution=institution,
            kind=kind,
            scope=scope,
        )
        value = row.next_value
        row.next_value = value + 1
        row.save(update_fields=["next_value", "updated_at"])
        return value


def generate_identifier(
    institution,
    kind: str,
    *,
    year: int,
    scope: str = "default",
) -> str:
    patterns = (institution.settings or {}).get("identifier_patterns") or {}
    pattern = patterns.get(kind, DEFAULT_PATTERNS.get(kind))
    if not pattern or "{seq" not in pattern:
        raise IdentifierError(f"invalid_identifier_pattern:{kind}")
    value = next_sequence_value(institution, kind, scope=scope)
    try:
        return pattern.format(
            institution_code=institution.code,
            year=year,
            YYYY=year,
            scope=scope,
            seq=value,
        )
    except (KeyError, ValueError, IndexError) as exc:
        raise IdentifierError(f"invalid_identifier_pattern:{kind}") from exc
