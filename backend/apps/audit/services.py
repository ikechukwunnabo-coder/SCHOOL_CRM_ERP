from __future__ import annotations

import logging
from typing import Any

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
    """Create an audit log entry without letting audit failures block the primary action."""
    req = request or get_current_request()
    resolved_actor = actor if actor is not None else get_current_user()
    is_authenticated = getattr(resolved_actor, "is_authenticated", False)
    if institution_id is None and is_authenticated:
        institution_id = getattr(resolved_actor, "institution_id", None)
    if campus_id is None and is_authenticated:
        campus_id = getattr(resolved_actor, "campus_id", None)
    try:
        return AuditLog.objects.create(
            actor=resolved_actor if is_authenticated else None,
            action=action[:150],
            target_type=target_type[:150],
            target_id=str(target_id)[:64] if target_id else "",
            institution_id=institution_id,
            campus_id=campus_id,
            reason=reason,
            change_summary=_redact(change_summary or {}),
            metadata=_redact(metadata or {}),
            ip_address=_get_ip(req),
        )
    except Exception:
        logger.exception("audit log write failed for action=%s", action)
        return None
