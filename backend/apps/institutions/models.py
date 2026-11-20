from django.db import models

from apps.core.models import TimeStampedModel


class Institution(TimeStampedModel):
    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Campus(TimeStampedModel):
    institution = models.ForeignKey(
        Institution,
        on_delete=models.PROTECT,
        related_name="campuses",
    )
    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=64)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["institution__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="uq_campus_institution_code",
            )
        ]

    def __str__(self) -> str:
        return f"{self.institution.code}:{self.code}"
