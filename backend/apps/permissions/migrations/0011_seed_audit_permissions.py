from django.db import migrations


def seed_audit_permissions(apps, schema_editor):
    from apps.permissions.grants import MODULE_GRANTS

    Permission = apps.get_model("app_permissions", "Permission")
    for verb, role_names in MODULE_GRANTS["audit"].items():
        Permission.objects.update_or_create(
            module="audit",
            verb=verb,
            resource="*",
            defaults={
                "code": f"audit.{verb}.*",
                "allowed_role_names": list(role_names),
                "scope_rules": {"institution": True, "campus": True},
            },
        )


def remove_audit_permissions(apps, schema_editor):
    Permission = apps.get_model("app_permissions", "Permission")
    Permission.objects.filter(module="audit").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("app_permissions", "0010_seed_dev_completion_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_audit_permissions, remove_audit_permissions),
    ]
