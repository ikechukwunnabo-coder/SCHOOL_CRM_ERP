import uuid

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class InstitutionScopedModel(TimeStampedModel):
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_set",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class AuditableModel(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
    )

    class Meta:
        abstract = True


class IdentifierSequence(TimeStampedModel):
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="identifier_sequences",
    )
    kind = models.CharField(max_length=64)
    scope = models.CharField(max_length=128, default="default")
    next_value = models.PositiveBigIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "kind", "scope"],
                name="uq_identifier_sequence_scope",
            )
        ]
        ordering = ["institution__code", "kind", "scope"]

    def __str__(self) -> str:
        return f"{self.institution.code}:{self.kind}:{self.scope}:{self.next_value}"
