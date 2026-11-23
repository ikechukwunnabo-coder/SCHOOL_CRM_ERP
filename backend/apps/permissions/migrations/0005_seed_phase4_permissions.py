from django.db import migrations


PHASE4_MODULES = ("examinations",)


def seed_phase4_permissions(apps, schema_editor):
    from apps.permissions.grants import MODULE_GRANTS

    Permission = apps.get_model("app_permissions", "Permission")
    for module in PHASE4_MODULES:
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


def remove_phase4_permissions(apps, schema_editor):
    Permission = apps.get_model("app_permissions", "Permission")
    Permission.objects.filter(module__in=PHASE4_MODULES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("app_permissions", "0004_seed_phase3_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_phase4_permissions, remove_phase4_permissions),
    ]
