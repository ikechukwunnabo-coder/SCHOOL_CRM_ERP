from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Role(TimeStampedModel):
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="roles",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                name="uq_role_institution_name",
            )
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        scope = self.institution.code if self.institution else "global"
        return f"{scope}:{self.name}"


class UserRole(TimeStampedModel):
    class ScopeType(models.TextChoices):
        INSTITUTION = "institution", "Institution"
        CAMPUS = "campus", "Campus"
        CLASS = "class", "Class/Arm"
        SUBJECT = "subject", "Subject"
        RECORD = "record", "Record"
        OWN = "own", "Own"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_roles",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_roles",
    )
    scope_type = models.CharField(
        max_length=20,
        choices=ScopeType.choices,
        default=ScopeType.INSTITUTION,
    )
    scope_ref_id = models.UUIDField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["scope_type", "scope_ref_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.role_id}:{self.scope_type}"


class Permission(TimeStampedModel):
    module = models.CharField(max_length=50)
    verb = models.CharField(max_length=30)
    resource = models.CharField(max_length=80, default="*")
    code = models.CharField(max_length=150, unique=True)
    allowed_role_names = models.JSONField(default=list, blank=True)
    scope_rules = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["module", "resource", "verb"]
        indexes = [models.Index(fields=["module", "verb", "resource"])]

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"{self.module}.{self.verb}.{self.resource}"
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.code


class RolePermission(TimeStampedModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="role_grants",
    )
    allowed = models.BooleanField(default=True)
    scope_rules = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="uq_role_permission_pair",
            )
        ]
        ordering = ["role__name", "permission__code"]

    def __str__(self) -> str:
        state = "allow" if self.allowed else "deny"
        return f"{self.role_id}:{self.permission_id}:{state}"
