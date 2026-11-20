from __future__ import annotations

from typing import Any

from .middleware import get_current_request, get_current_user
from .models import AuditLog


def _get_ip(request) -> str | None:
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


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
) -> AuditLog:
    """Create an audit log entry. Best-effort, should not break primary flow."""
    req = request or get_current_request()
    resolved_actor = actor if actor is not None else get_current_user()
    try:
        return AuditLog.objects.create(
            actor=resolved_actor if getattr(resolved_actor, "is_authenticated", False) else None,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else "",
            institution_id=institution_id,
            campus_id=campus_id,
            reason=reason or "",
            change_summary=change_summary or {},
            metadata=metadata or {},
            ip_address=_get_ip(req),
        )
    except Exception:
        # Audit logging must not block core actions in foundation phase; failures
        # should be captured by observability in later hardening.
        return AuditLog(action=action)
