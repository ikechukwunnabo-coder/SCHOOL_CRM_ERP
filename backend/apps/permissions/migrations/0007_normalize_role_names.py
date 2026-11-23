from django.db import migrations


ALL_MODULES = (
    "admissions",
    "students",
    "documents",
    "imports",
    "employees",
    "academics",
    "teaching",
    "attendance",
    "examinations",
    "transcripts",
)


def normalize_roles_and_permissions(apps, schema_editor):
    from apps.permissions.grants import MODULE_GRANTS
    from apps.permissions.roles import LEGACY_ROLE_MIGRATIONS

    Role = apps.get_model("app_permissions", "Role")
    UserRole = apps.get_model("app_permissions", "UserRole")
    Permission = apps.get_model("app_permissions", "Permission")

    for legacy_name, canonical_names in LEGACY_ROLE_MIGRATIONS.items():
        legacy_roles = Role.objects.filter(name=legacy_name)
        for legacy_role in legacy_roles:
            replacement_roles = []
            for canonical_name in canonical_names:
                canonical_role, _ = Role.objects.get_or_create(
                    institution_id=legacy_role.institution_id,
                    name=canonical_name,
                    defaults={
                        "description": legacy_role.description,
                        "is_system": legacy_role.is_system,
                    },
                )
                replacement_roles.append(canonical_role)
            for assignment in UserRole.objects.filter(role_id=legacy_role.id):
                for canonical_role in replacement_roles:
                    exists = UserRole.objects.filter(
                        user_id=assignment.user_id,
                        role_id=canonical_role.id,
                        scope_type=assignment.scope_type,
                        scope_ref_id=assignment.scope_ref_id,
                    ).exists()
                    if exists:
                        continue
                    UserRole.objects.create(
                        user_id=assignment.user_id,
                        role_id=canonical_role.id,
                        scope_type=assignment.scope_type,
                        scope_ref_id=assignment.scope_ref_id,
                        is_active=assignment.is_active,
                    )
        legacy_roles.delete()

    for module in ALL_MODULES:
        for verb, role_names in MODULE_GRANTS[module].items():
            Permission.objects.update_or_create(
                module=module,
                verb=verb,
                resource="*",
                defaults={
                    "code": f"{module}.{verb}.*",
                    "allowed_role_names": list(role_names),
                    "scope_rules": {"institution": True, "campus": True},
                },
            )


class Migration(migrations.Migration):
    dependencies = [
        ("app_permissions", "0006_seed_phase4_transcript_permissions"),
    ]

    operations = [
        migrations.RunPython(normalize_roles_and_permissions, migrations.RunPython.noop),
    ]
