from django.db import models

from apps.core.models import TimeStampedModel


class AlumniRecord(TimeStampedModel):
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="alumni_records",
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="alumni_records",
    )
    student = models.OneToOneField(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="alumni_record",
    )
    graduation_event = models.OneToOneField(
        "students.StudentLifecycleEvent",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="alumni_record",
    )
    graduation_date = models.DateField()
    graduation_reference = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["institution__code", "student__admission_number", "-graduation_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "student"],
                name="uq_alumni_record_institution_student",
            )
        ]
        indexes = [models.Index(fields=["institution", "campus", "graduation_date"])]

    def __str__(self) -> str:
        return f"{self.student.admission_number}:{self.graduation_date}"
