from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Employee(TimeStampedModel):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        CONTRACT = "contract", "Contract"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    institution = models.ForeignKey(
        "institutions.Institution", on_delete=models.PROTECT, related_name="employees"
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="employees",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee",
    )
    employee_number = models.CharField(max_length=64)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=150, blank=True)
    job_title = models.CharField(max_length=150, blank=True)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["institution__code", "employee_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "employee_number"], name="uq_employee_institution_number"
            )
        ]
        indexes = [models.Index(fields=["institution", "campus", "status"])]

    def __str__(self) -> str:
        return f"{self.employee_number}: {self.first_name} {self.last_name}".strip()
