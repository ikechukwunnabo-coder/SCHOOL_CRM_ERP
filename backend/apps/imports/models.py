from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class ImportJob(TimeStampedModel):
    class Dataset(models.TextChoices):
        STUDENTS = "students", "Students"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PREVIEWED = "previewed", "Previewed"
        APPROVED = "approved", "Approved"
        APPLIED = "applied", "Applied"
        FAILED = "failed", "Failed"

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="import_jobs",
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_jobs",
    )
    dataset = models.CharField(max_length=30, choices=Dataset.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    source_name = models.CharField(max_length=255)
    source_ref = models.CharField(max_length=255, blank=True)
    payload = models.TextField(blank=True)
    dry_run = models.BooleanField(default=True)
    mapping = models.JSONField(default=dict, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="import_jobs_created",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_jobs_approved",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["institution", "dataset", "status"])]

    def __str__(self) -> str:
        return f"{self.dataset}:{self.source_name}:{self.status}"


class ImportRowError(TimeStampedModel):
    job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name="row_errors")
    row_number = models.PositiveIntegerField()
    field = models.CharField(max_length=80, blank=True)
    message = models.CharField(max_length=255)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["row_number", "field"]
