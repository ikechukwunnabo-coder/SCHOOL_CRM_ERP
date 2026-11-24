from django.db import migrations


FINANCE_MODULES = ("finance",)


def seed_finance_permissions(apps, schema_editor):
    from apps.permissions.grants import MODULE_GRANTS

    Permission = apps.get_model("app_permissions", "Permission")
    for module in FINANCE_MODULES:
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


def remove_finance_permissions(apps, schema_editor):
    Permission = apps.get_model("app_permissions", "Permission")
    Permission.objects.filter(module__in=FINANCE_MODULES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("app_permissions", "0008_seed_alumni_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_finance_permissions, remove_finance_permissions),
    ]
