import hashlib

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Student(TimeStampedModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        UNSPECIFIED = "unspecified", "Unspecified"

    class LifecycleStatus(models.TextChoices):
        APPLICANT = "applicant", "Applicant"
        ADMITTED = "admitted", "Admitted"
        ENROLLED = "enrolled", "Enrolled"
        ACTIVE = "active", "Active"
        PROMOTED = "promoted", "Promoted"
        REPEATED = "repeated", "Repeated"
        TRANSFERRED = "transferred", "Transferred"
        WITHDRAWN = "withdrawn", "Withdrawn"
        GRADUATED = "graduated", "Graduated"

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="students",
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="students",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profile",
    )
    source_application = models.OneToOneField(
        "admissions.Application",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="student",
    )
    admission_number = models.CharField(max_length=64)
    identity_key = models.CharField(max_length=64, editable=False)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        default=Gender.UNSPECIFIED,
    )
    status = models.CharField(
        max_length=20,
        choices=LifecycleStatus.choices,
        default=LifecycleStatus.ADMITTED,
    )
    admission_date = models.DateField()

    class Meta:
        ordering = ["institution__code", "admission_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "admission_number"],
                name="uq_student_institution_admission_number",
            ),
            models.UniqueConstraint(
                fields=["institution", "identity_key"],
                name="uq_student_identity",
            ),
        ]
        indexes = [models.Index(fields=["institution", "campus", "status"])]

    def __str__(self) -> str:
        return f"{self.admission_number}: {self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        raw = (
            f"{self.first_name.strip().lower()}|"
            f"{self.last_name.strip().lower()}|"
            f"{self.date_of_birth.isoformat()}"
        )
        self.identity_key = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        super().save(*args, **kwargs)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class StudentGuardian(TimeStampedModel):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="guardian_links",
    )
    guardian = models.ForeignKey(
        "guardians.Guardian",
        on_delete=models.PROTECT,
        related_name="student_links",
    )
    relationship = models.CharField(max_length=64)
    is_primary = models.BooleanField(default=False)
    financial_responsibility = models.BooleanField(default=False)
    authorized_pickup = models.BooleanField(default=False)
    portal_access = models.BooleanField(default=False)

    class Meta:
        ordering = ["student__admission_number", "guardian__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "guardian"],
                name="uq_student_guardian_pair",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student_id}:{self.guardian_id}:{self.relationship}"

    @property
    def institution_id(self):
        return self.student.institution_id

    @property
    def campus_id(self):
        return self.student.campus_id


class StudentLifecycleEvent(TimeStampedModel):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="lifecycle_events",
    )
    from_status = models.CharField(max_length=20, choices=Student.LifecycleStatus.choices)
    to_status = models.CharField(max_length=20, choices=Student.LifecycleStatus.choices)
    effective_date = models.DateField()
    reason = models.TextField(blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_lifecycle_events",
    )

    class Meta:
        ordering = ["-effective_date", "-created_at"]
        indexes = [models.Index(fields=["student", "effective_date"])]

    def __str__(self) -> str:
        return f"{self.student_id}:{self.from_status}->{self.to_status}"

    @property
    def institution_id(self):
        return self.student.institution_id

    @property
    def campus_id(self):
        return self.student.campus_id
