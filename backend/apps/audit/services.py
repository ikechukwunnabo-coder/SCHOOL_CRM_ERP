from __future__ import annotations

import logging
import uuid
from typing import Any

from django.db import connection, transaction
from django.utils import timezone

from .middleware import get_current_request, get_current_user
from .models import AuditLog

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "csrftoken",
    "sessionid",
}
_GLOBAL_SCOPE_KEY = uuid.UUID("00000000-0000-0000-0000-000000000000")


def _get_ip(request) -> str | None:
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if str(key).lower() in _SENSITIVE_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


def _normalize_uuid(value):
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _scope_lock_key(institution_id) -> int:
    key = institution_id or _GLOBAL_SCOPE_KEY
    value = key.int & 0xFFFFFFFFFFFFFFFF
    if value >= 0x8000000000000000:
        value -= 0x10000000000000000
    return value


def verify_audit_chain(*, institution_id=None) -> dict[str, Any]:
    normalized_institution_id = _normalize_uuid(institution_id)
    qs = AuditLog.objects.all()
    if institution_id is None:
        qs = qs.filter(institution_id__isnull=True)
        scope_label = "global"
    else:
        qs = qs.filter(institution_id=normalized_institution_id)
        scope_label = str(normalized_institution_id)
    entries = list(qs.order_by("sequence_number", "created_at", "id"))
    errors: list[dict[str, Any]] = []
    expected_sequence = 1
    previous_hash = ""
    for entry in entries:
        if entry.sequence_number != expected_sequence:
            errors.append(
                {
                    "id": str(entry.id),
                    "sequence_number": entry.sequence_number,
                    "error": "missing_or_out_of_order_sequence",
                    "expected_sequence_number": expected_sequence,
                }
            )
        if (entry.previous_hash or "") != previous_hash:
            errors.append(
                {
                    "id": str(entry.id),
                    "sequence_number": entry.sequence_number,
                    "error": "broken_previous_hash",
                }
            )
        computed_hash = entry.compute_entry_hash()
        if entry.entry_hash != computed_hash:
            errors.append(
                {
                    "id": str(entry.id),
                    "sequence_number": entry.sequence_number,
                    "error": "entry_hash_mismatch",
                }
            )
        previous_hash = entry.entry_hash or computed_hash
        expected_sequence = entry.sequence_number + 1
    return {
        "institution_id": scope_label,
        "count": len(entries),
        "valid": not errors,
        "errors": errors,
    }


def log_event(
    action: str,
    *,
    actor=None,
    target_type: str = "",
    target_id: str = "",
    institution_id=None,
    campus_id=None,
    reason: str = "",
    change_summary: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    request=None,
) -> AuditLog | None:
    req = request or get_current_request()
    resolved_actor = actor if actor is not None else get_current_user()
    is_authenticated = getattr(resolved_actor, "is_authenticated", False)
    if institution_id is None and is_authenticated:
        institution_id = getattr(resolved_actor, "institution_id", None)
    if campus_id is None and is_authenticated:
        campus_id = getattr(resolved_actor, "campus_id", None)
    normalized_institution_id = _normalize_uuid(institution_id)
    normalized_campus_id = _normalize_uuid(campus_id)
    redacted_change_summary = _redact(change_summary or {})
    redacted_metadata = _redact(metadata or {})
    target = str(target_id)[:64] if target_id else ""
    action_value = action[:150]
    target_type_value = target_type[:150]
    ip_address = _get_ip(req)
    actor_obj = resolved_actor if is_authenticated else None
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(%s::bigint)",
                    [_scope_lock_key(normalized_institution_id)],
                )
            last_entry = (
                AuditLog.objects.filter(institution_id=normalized_institution_id)
                .order_by("-sequence_number")
                .only("sequence_number", "entry_hash")
                .first()
            )
            sequence_number = 1 if last_entry is None else last_entry.sequence_number + 1
            previous_hash = "" if last_entry is None else (last_entry.entry_hash or "")
            entry = AuditLog(
                actor=actor_obj,
                action=action_value,
                target_type=target_type_value,
                target_id=target,
                institution_id=normalized_institution_id,
                campus_id=normalized_campus_id,
                reason=reason,
                change_summary=redacted_change_summary,
                metadata=redacted_metadata,
                ip_address=ip_address,
                sequence_number=sequence_number,
                previous_hash=previous_hash,
            )
            created_at = timezone.now()
            entry.created_at = created_at
            entry.entry_hash = entry.compute_entry_hash()
            entry.save(force_insert=True)
            return entry
    except Exception:
        logger.exception("audit log write failed for action=%s", action)
        return None
