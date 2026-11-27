from django.db import migrations


def seed_cms_permissions(apps, schema_editor):
    from apps.permissions.grants import MODULE_GRANTS

    Permission = apps.get_model("app_permissions", "Permission")
    for verb, role_names in MODULE_GRANTS["cms"].items():
        Permission.objects.update_or_create(
            module="cms",
            verb=verb,
            resource="*",
            defaults={
                "code": f"cms.{verb}.*",
                "allowed_role_names": list(role_names),
                "scope_rules": {"institution": True, "campus": True},
            },
        )


def remove_cms_permissions(apps, schema_editor):
    Permission = apps.get_model("app_permissions", "Permission")
    Permission.objects.filter(module="cms").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("app_permissions", "0011_seed_audit_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_cms_permissions, remove_cms_permissions),
    ]
