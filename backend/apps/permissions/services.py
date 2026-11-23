from __future__ import annotations

from django.db.models import Q

from apps.institutions.models import Campus

from .models import Permission
from .roles import normalize_role_names


def _is_privileged(user) -> bool:
    return bool(user and getattr(user, "is_authenticated", False) and user.is_superuser)


def user_has_active_role(user, role_name: str | None = None, *, institution_id=None) -> bool:
    """Check whether the user holds an active role, optionally scoped to an institution."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    qs = user.user_roles.filter(is_active=True).select_related("role")
    if role_name:
        expected = normalize_role_names([role_name]) | {role_name}
        qs = qs.filter(role__name__in=expected)
    if institution_id is not None:
        qs = qs.filter(role__institution_id=institution_id)
    return qs.exists()


def user_has_active_role_for_institution(user, institution_id) -> bool:
    """Check for an active role valid for the given institution.

    Global roles (no institution) apply everywhere; institution roles apply only
    to their own institution. Superusers bypass the role requirement.
    """
    if _is_privileged(user):
        return True
    if not user or not getattr(user, "is_authenticated", False) or institution_id is None:
        return False
    if user.institution_id != institution_id:
        return False
    return (
        user.user_roles.filter(
            is_active=True,
            scope_type__in=[
                "institution",
                "campus",
                "class",
                "subject",
                "record",
                "own",
            ],
        )
        .filter(Q(role__institution_id__isnull=True) | Q(role__institution_id=institution_id))
        .exists()
    )


def get_user_role_names(user) -> list[str]:
    if not user or not getattr(user, "is_authenticated", False):
        return []
    held = (
        user.user_roles.filter(is_active=True)
        .select_related("role")
        .values_list("role__name", flat=True)
        .distinct()
    )
    return sorted(normalize_role_names(held))


def user_has_module_permission(user, module: str, verb: str, *, resource: str = "*") -> bool:
    """Check configurable per-verb grants after baseline institution checks."""
    if _is_privileged(user):
        return True
    institution_id = getattr(user, "institution_id", None)
    if not user_has_active_role_for_institution(user, institution_id):
        return False
    held = set(get_user_role_names(user))
    if not held:
        return False
    permissions = (
        Permission.objects.filter(module=module, verb=verb)
        .filter(Q(resource=resource) | Q(resource="*"))
        .prefetch_related("role_grants__role")
    )
    for permission in permissions:
        if normalize_role_names(permission.allowed_role_names) & held:
            return True
        if any(
            grant.allowed and grant.role.name in normalize_role_names(held)
            for grant in permission.role_grants.all()
        ):
            return True
    return False


def get_user_role_assignments(user) -> list[dict]:
    """Return active role assignments for auth/context responses."""
    if not user or not getattr(user, "is_authenticated", False):
        return []
    assignments = (
        user.user_roles.filter(is_active=True)
        .select_related("role", "role__institution")
        .order_by("role__name")
    )
    result = []
    for ur in assignments:
        role = ur.role
        result.append(
            {
                "role": role.name,
                "role_id": str(role.id),
                "is_system": role.is_system,
                "scope_type": ur.scope_type,
                "scope_ref_id": str(ur.scope_ref_id) if ur.scope_ref_id else None,
                "institution_id": str(role.institution_id) if role.institution_id else None,
            }
        )
    return result


def user_can_access_institution(user, institution_id) -> bool:
    """Server-side institution scope check; deny by default."""
    if _is_privileged(user):
        return True
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if institution_id is None or user.institution_id != institution_id:
        return False
    return user_has_active_role_for_institution(user, institution_id)


def user_can_access_campus_id(user, campus_id) -> bool:
    """Server-side campus scope check for a campus identifier."""
    if _is_privileged(user):
        return True
    if not user_can_access_institution(user, user.institution_id):
        return False
    if campus_id is None or user.campus_id is None:
        return True
    return user.campus_id == campus_id


def user_can_access_campus(user, campus: Campus) -> bool:
    """Server-side campus scope check within an accessible institution."""
    if _is_privileged(user):
        return True
    if not user_can_access_institution(user, campus.institution_id):
        return False
    return user_can_access_campus_id(user, campus.id)
