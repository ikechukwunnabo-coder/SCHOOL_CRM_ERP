from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.core.storage import private_document_storage


class TranscriptKind(models.TextChoices):
    PROVISIONAL = "provisional", "Provisional"
    OFFICIAL = "official", "Official"


class TranscriptRequest(TimeStampedModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        GENERATED = "generated", "Generated"
        ISSUED = "issued", "Issued"

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="transcript_requests",
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transcript_requests",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="transcript_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_transcripts",
    )
    purpose = models.TextField()
    requested_kind = models.CharField(
        max_length=20, choices=TranscriptKind.choices, default=TranscriptKind.OFFICIAL
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    decision_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_transcript_requests",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_transcript_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["institution__code", "-created_at"]
        indexes = [
            models.Index(fields=["institution", "campus", "status"]),
        ]


class Transcript(TimeStampedModel):
    class Status(models.TextChoices):
        GENERATED = "generated", "Generated"
        ISSUED = "issued", "Issued"
        CORRECTED = "corrected", "Corrected"
        SUPERSEDED = "superseded", "Superseded"
        REVOKED = "revoked", "Revoked"

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="transcripts",
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transcripts",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="transcripts",
    )
    request = models.ForeignKey(
        TranscriptRequest,
        on_delete=models.PROTECT,
        related_name="transcripts",
    )
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="replacements",
    )
    reference_number = models.CharField(max_length=64)
    version = models.PositiveIntegerField(default=1)
    kind = models.CharField(
        max_length=20, choices=TranscriptKind.choices, default=TranscriptKind.PROVISIONAL
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GENERATED)
    verification_token_hash = models.CharField(max_length=64, unique=True)
    verification_token_issued_at = models.DateTimeField(default=timezone.now)
    verification_revoked_at = models.DateTimeField(null=True, blank=True)
    file = models.FileField(
        storage=private_document_storage,
        upload_to="transcripts/%Y/%m/",
        max_length=500,
        blank=True,
    )
    file_ref = models.CharField(max_length=500, blank=True)
    content_type = models.CharField(max_length=150, default="application/pdf")
    size_bytes = models.PositiveBigIntegerField(default=0)
    pdf_sha256 = models.CharField(max_length=64, blank=True)
    template_version = models.CharField(max_length=40, default="default-v1")
    issued_to = models.CharField(max_length=200, blank=True)
    issue_purpose = models.TextField(blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_transcripts",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_transcripts",
    )
    issued_at = models.DateTimeField(null=True, blank=True)
    document_snapshot = models.JSONField(default=dict)
    results_snapshot = models.JSONField(default=list)
    completeness = models.JSONField(default=dict)

    class Meta:
        ordering = ["institution__code", "student__admission_number", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "reference_number"],
                name="uq_transcript_institution_reference",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gt=0),
                name="ck_transcript_version_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["institution", "campus", "status"]),
        ]


class TranscriptEvent(TimeStampedModel):
    request = models.ForeignKey(
        TranscriptRequest,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="events",
    )
    transcript = models.ForeignKey(
        Transcript,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="events",
    )
    action = models.CharField(max_length=50)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transcript_events",
    )
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["transcript", "action"]),
        ]

    @property
    def institution_id(self):
        if self.transcript_id:
            return self.transcript.institution_id
        return self.request.institution_id

    @property
    def campus_id(self):
        if self.transcript_id:
            return self.transcript.campus_id
        return self.request.campus_id


class TranscriptVerification(TimeStampedModel):
    class Outcome(models.TextChoices):
        VALID = "valid", "Valid"
        INVALID = "invalid", "Invalid"
        REVOKED = "revoked", "Revoked"
        SUPERSEDED = "superseded", "Superseded"
        INVALID_STATE = "invalid_state", "Invalid State"

    transcript = models.ForeignKey(
        Transcript,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verifications",
    )
    token_hash = models.CharField(max_length=64)
    outcome = models.CharField(max_length=20, choices=Outcome.choices)
    checked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-checked_at"]
        indexes = [
            models.Index(fields=["token_hash", "outcome"]),
        ]

    @property
    def institution_id(self):
        return self.transcript.institution_id if self.transcript_id else None

    @property
    def campus_id(self):
        return self.transcript.campus_id if self.transcript_id else None
