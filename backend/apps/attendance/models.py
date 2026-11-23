from django.conf import settings
from django.db import models

from apps.academics.models import AcademicSession, Arm, ClassLevel, SubjectOffering, Term
from apps.core.models import TimeStampedModel


class AttendanceSession(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    institution = models.ForeignKey(
        "institutions.Institution", on_delete=models.PROTECT, related_name="attendance_sessions"
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="attendance_sessions",
    )
    session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name="attendance_sessions"
    )
    term = models.ForeignKey(
        Term, on_delete=models.PROTECT, null=True, blank=True, related_name="attendance_sessions"
    )
    class_level = models.ForeignKey(
        ClassLevel, on_delete=models.PROTECT, related_name="attendance_sessions"
    )
    arm = models.ForeignKey(
        Arm, on_delete=models.PROTECT, null=True, blank=True, related_name="attendance_sessions"
    )
    offering = models.ForeignKey(
        SubjectOffering, on_delete=models.PROTECT, related_name="attendance_sessions"
    )
    attendance_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_sessions_closed",
    )

    class Meta:
        ordering = ["-attendance_date", "class_level__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["offering", "attendance_date"], name="uq_attendance_offering_date"
            )
        ]


class AttendanceRecord(TimeStampedModel):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        EXCUSED = "excused", "Excused"

    attendance_session = models.ForeignKey(
        AttendanceSession, on_delete=models.CASCADE, related_name="records"
    )
    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="attendance_records"
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_marked",
    )
    marked_at = models.DateTimeField(auto_now=True)
    correction_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["attendance_session__attendance_date", "student__admission_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["attendance_session", "student"], name="uq_attendance_session_student"
            )
        ]

    @property
    def institution_id(self):
        return self.attendance_session.institution_id

    @property
    def campus_id(self):
        return self.attendance_session.campus_id


class TeacherAttendanceRecord(TimeStampedModel):
    class ApprovalStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="teacher_attendance_records",
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="teacher_attendance_records",
    )
    employee = models.ForeignKey(
        "app_employees.Employee",
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )
    attendance_date = models.DateField()
    status = models.CharField(max_length=20, choices=AttendanceRecord.Status.choices)
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.DRAFT,
    )
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teacher_attendance_marked",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teacher_attendance_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-attendance_date", "employee__employee_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "attendance_date"],
                name="uq_teacher_attendance_employee_date",
            )
        ]
        indexes = [
            models.Index(fields=["institution", "campus", "attendance_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee_id}:{self.attendance_date}:{self.status}"


class AttendanceCorrection(TimeStampedModel):
    record = models.ForeignKey(
        AttendanceRecord, on_delete=models.PROTECT, related_name="corrections"
    )
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    reason = models.TextField()
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_corrections_requested",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_corrections_approved",
    )

    class Meta:
        ordering = ["-created_at"]

    @property
    def institution_id(self):
        return self.record.institution_id

    @property
    def campus_id(self):
        return self.record.campus_id
