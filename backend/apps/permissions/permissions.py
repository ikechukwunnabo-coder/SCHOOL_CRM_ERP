from rest_framework.permissions import BasePermission


class IsAuthenticatedAndActive(BasePermission):
    """Baseline permission: authenticated, active user account."""

    message = "Authentication with an active account is required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_active)


class HasInstitutionContext(BasePermission):
    """Foundation guard: require institution context for non-superusers."""

    message = "Institution context is required for this action."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return bool(getattr(user, "institution_id", None))
