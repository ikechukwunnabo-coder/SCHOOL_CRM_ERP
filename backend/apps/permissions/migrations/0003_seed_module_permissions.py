from django.db import migrations

from apps.permissions.grants import MODULE_GRANTS


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("app_permissions", "Permission")
    for module, verbs in MODULE_GRANTS.items():
        for verb, role_names in verbs.items():
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


def remove_permissions(apps, schema_editor):
    Permission = apps.get_model("app_permissions", "Permission")
    Permission.objects.filter(module__in=MODULE_GRANTS.keys()).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("app_permissions", "0002_permission_rolepermission"),
    ]

    operations = [
        migrations.RunPython(seed_permissions, remove_permissions),
    ]
