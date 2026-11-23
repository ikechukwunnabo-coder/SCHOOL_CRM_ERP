from django.conf import settings
from django.db import models

from apps.academics.models import AcademicSession, Arm, ClassLevel, SubjectOffering, Term
from apps.core.models import TimeStampedModel
from apps.employees.models import Employee


class TeacherAssignment(TimeStampedModel):
    class Role(models.TextChoices):
        LEAD = "lead", "Lead"
        ASSISTANT = "assistant", "Assistant"
        SUBSTITUTE = "substitute", "Substitute"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    institution = models.ForeignKey(
        "institutions.Institution", on_delete=models.PROTECT, related_name="teacher_assignments"
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="teacher_assignments",
    )
    session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name="teacher_assignments"
    )
    term = models.ForeignKey(
        Term, on_delete=models.PROTECT, null=True, blank=True, related_name="teacher_assignments"
    )
    class_level = models.ForeignKey(
        ClassLevel, on_delete=models.PROTECT, related_name="teacher_assignments"
    )
    arm = models.ForeignKey(
        Arm, on_delete=models.PROTECT, null=True, blank=True, related_name="teacher_assignments"
    )
    offering = models.ForeignKey(
        SubjectOffering, on_delete=models.PROTECT, related_name="teacher_assignments"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="teacher_assignments"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.LEAD)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField()
    end_date = models.DateField()
    workload_hours = models.PositiveIntegerField(default=0)
    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments_authorized",
    )

    class Meta:
        ordering = ["session__code", "employee__employee_number"]
        indexes = [
            models.Index(fields=["institution", "campus", "status", "start_date", "end_date"])
        ]

    def __str__(self) -> str:
        return f"{self.employee_id}:{self.offering_id}:{self.role}"


class Timetable(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name="timetables"
    )
    class_level = models.ForeignKey(ClassLevel, on_delete=models.PROTECT, related_name="timetables")
    arm = models.ForeignKey(
        Arm, on_delete=models.PROTECT, null=True, blank=True, related_name="timetables"
    )
    name = models.CharField(max_length=100)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ["session__code", "class_level__code", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "class_level", "arm", "version"], name="uq_timetable_version"
            )
        ]

    @property
    def institution_id(self):
        return self.session.institution_id

    @property
    def campus_id(self):
        return self.session.campus_id


class TimetableSlot(TimeStampedModel):
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name="slots")
    day_of_week = models.PositiveSmallIntegerField()
    period = models.PositiveSmallIntegerField()
    offering = models.ForeignKey(
        SubjectOffering, on_delete=models.PROTECT, related_name="timetable_slots"
    )
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="timetable_slots")
    room = models.CharField(max_length=100)

    class Meta:
        ordering = ["timetable__version", "day_of_week", "period"]
        constraints = [
            models.UniqueConstraint(
                fields=["timetable", "day_of_week", "period"], name="uq_slot_timetable_day_period"
            )
        ]

    @property
    def institution_id(self):
        return self.timetable.institution_id

    @property
    def campus_id(self):
        return self.timetable.campus_id
