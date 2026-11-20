from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class Guardian(TimeStampedModel):
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="guardians",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    preferences = models.JSONField(default=dict, blank=True)
    consent = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guardians_created",
    )

    class Meta:
        ordering = ["institution__code", "last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "email"],
                condition=~Q(email=""),
                name="uq_guardian_institution_email",
            )
        ]
        indexes = [models.Index(fields=["institution", "last_name", "first_name"])]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
