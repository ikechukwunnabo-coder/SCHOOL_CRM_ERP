from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class PersonDetails(models.Model):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=20,
        choices=[
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
            ("unspecified", "Unspecified"),
        ],
        default="unspecified",
    )
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)

    class Meta:
        abstract = True

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Enquiry(PersonDetails, TimeStampedModel):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        CONVERTED = "converted", "Converted"
        CLOSED = "closed", "Closed"

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="enquiries",
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="enquiries",
    )
    intended_class = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enquiries_created",
    )

    class Meta:
        ordering = ["institution__code", "-created_at"]
        indexes = [models.Index(fields=["institution", "campus", "status"])]

    def __str__(self) -> str:
        return f"ENQ-{self.pk}: {self.full_name}"


class Application(PersonDetails, TimeStampedModel):
    class Status(models.TextChoices):
        STARTED = "started", "Application Started"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        ASSESSMENT = "assessment", "Assessment/Interview"
        APPROVED = "approved", "Approved"
        OFFERED = "offered", "Offered"
        ACCEPTED = "accepted", "Accepted"
        ENROLLED = "enrolled", "Enrolled"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        WAITLISTED = "waitlisted", "Waitlisted"
        DEFERRED = "deferred", "Deferred"

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="applications",
    )
    enquiry = models.ForeignKey(
        Enquiry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    application_number = models.CharField(max_length=64)
    cycle = models.CharField(max_length=20)
    intended_class = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.STARTED,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications_created",
    )

    class Meta:
        ordering = ["institution__code", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "application_number"],
                name="uq_application_institution_number",
            )
        ]
        indexes = [models.Index(fields=["institution", "campus", "status"])]

    def __str__(self) -> str:
        return f"{self.application_number}: {self.full_name}"


class AdmissionDecision(TimeStampedModel):
    class Outcome(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WAITLISTED = "waitlisted", "Waitlisted"
        DEFERRED = "deferred", "Deferred"

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="decision",
    )
    outcome = models.CharField(max_length=20, choices=Outcome.choices)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admission_decisions",
    )
    decided_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-decided_at"]

    def __str__(self) -> str:
        return f"{self.application_id}:{self.outcome}"

    @property
    def institution_id(self):
        return self.application.institution_id

    @property
    def campus_id(self):
        return self.application.campus_id


class ApplicationDocument(TimeStampedModel):
    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    checklist_item = models.CharField(max_length=150)
    original_name = models.CharField(max_length=255)
    file_ref = models.CharField(max_length=500)
    content_type = models.CharField(max_length=150, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="application_documents_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["application__application_number", "checklist_item"]
        indexes = [models.Index(fields=["application", "review_status"])]

    def __str__(self) -> str:
        return f"{self.application_id}:{self.checklist_item}"

    @property
    def institution_id(self):
        return self.application.institution_id

    @property
    def campus_id(self):
        return self.application.campus_id
