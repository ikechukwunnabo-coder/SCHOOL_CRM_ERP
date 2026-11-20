from __future__ import annotations

from django.db.models import Q

from apps.institutions.models import Campus


def _is_privileged(user) -> bool:
    return bool(user and getattr(user, "is_authenticated", False) and user.is_superuser)


def user_has_active_role(user, role_name: str | None = None, *, institution_id=None) -> bool:
    """Check whether the user holds an active role, optionally scoped to an institution."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    qs = user.user_roles.filter(is_active=True)
    if role_name:
        qs = qs.filter(role__name=role_name)
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
    return list(
        user.user_roles.filter(is_active=True)
        .select_related("role")
        .values_list("role__name", flat=True)
        .distinct()
    )


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


def user_can_access_campus(user, campus: Campus) -> bool:
    """Server-side campus scope check within an accessible institution."""
    if _is_privileged(user):
        return True
    if not user_can_access_institution(user, campus.institution_id):
        return False
    if user.campus_id is None:
        return True
    return user.campus_id == campus.id
