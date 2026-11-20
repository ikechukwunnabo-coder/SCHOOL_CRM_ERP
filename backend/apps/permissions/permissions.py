from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.audit.services import log_event
from apps.institutions.models import Institution

from .services import (
    user_can_access_campus,
    user_can_access_institution,
    user_has_active_role_for_institution,
)


def _deny(request, *, reason: str, target_type: str, target_id="", metadata=None) -> bool:
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        log_event(
            "authz.denied",
            actor=user,
            target_type=target_type,
            target_id=target_id,
            institution_id=getattr(user, "institution_id", None),
            campus_id=getattr(user, "campus_id", None),
            reason=reason,
            metadata=metadata or {},
            request=request,
        )
    return False


class IsAuthenticatedAndActive(BasePermission):
    """Baseline permission: authenticated, active user account."""

    message = "Authentication with an active account is required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_active)


class HasInstitutionContext(BasePermission):
    """Require an institution context for non-superusers."""

    message = "Institution context is required for this action."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.is_superuser:
            return True
        if not getattr(user, "institution_id", None):
            return _deny(
                request,
                reason="missing_institution_context",
                target_type="permissions.InstitutionContext",
            )
        return True


class HasActiveInstitutionRole(BasePermission):
    """Require an active role valid for the caller's institution."""

    message = "An active role for this institution is required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.is_superuser:
            return True
        institution_id = getattr(user, "institution_id", None)
        if not institution_id or not user_has_active_role_for_institution(user, institution_id):
            return _deny(
                request,
                reason="missing_active_institution_role",
                target_type="permissions.Role",
            )
        return True


class IsInstitutionScoped(BasePermission):
    """Object-level guard: the target must belong to the caller's institution."""

    message = "The requested resource is outside your institution scope."

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or not user.is_active:
            return False
        institution_id = (
            obj.id if isinstance(obj, Institution) else getattr(obj, "institution_id", None)
        )
        if user_can_access_institution(user, institution_id):
            return True
        return _deny(
            request,
            reason="cross_institution_access",
            target_type=type(obj).__name__,
            target_id=str(getattr(obj, "pk", "")),
        )


class IsCampusScoped(BasePermission):
    """Object-level guard: the target must be within the caller's campus scope."""

    message = "The requested resource is outside your campus scope."

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user_can_access_campus(user, obj):
            return True
        return _deny(
            request,
            reason="cross_campus_access",
            target_type=type(obj).__name__,
            target_id=str(getattr(obj, "pk", "")),
        )
