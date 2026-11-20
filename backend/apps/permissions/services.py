from __future__ import annotations


def user_has_active_role(user, role_name: str | None = None, *, institution_id=None) -> bool:
    """Minimal RBAC helper for foundation checks."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    qs = user.user_roles.filter(is_active=True)
    if role_name:
        qs = qs.filter(role__name=role_name)
    if institution_id is not None:
        qs = qs.filter(role__institution_id=institution_id)
    return qs.exists()


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
    """Return active role assignments for auth/context responses (foundation)."""
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
