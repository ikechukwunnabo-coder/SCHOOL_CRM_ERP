from django.db import models

from apps.core.models import TimeStampedModel


class AcademicSession(TimeStampedModel):
    institution = models.ForeignKey(
        "institutions.Institution", on_delete=models.PROTECT, related_name="academic_sessions"
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="academic_sessions",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["institution__code", "-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"], name="uq_session_institution_code"
            ),
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="ck_session_date_order",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Term(TimeStampedModel):
    session = models.ForeignKey(AcademicSession, on_delete=models.PROTECT, related_name="terms")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["session__code", "start_date"]
        constraints = [
            models.UniqueConstraint(fields=["session", "code"], name="uq_term_session_code"),
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="ck_term_date_order",
            ),
        ]

    @property
    def institution_id(self):
        return self.session.institution_id

    @property
    def campus_id(self):
        return self.session.campus_id


class ClassLevel(TimeStampedModel):
    institution = models.ForeignKey(
        "institutions.Institution", on_delete=models.PROTECT, related_name="class_levels"
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="class_levels",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["institution__code", "sequence", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"], name="uq_class_level_institution_code"
            )
        ]


class Arm(TimeStampedModel):
    class_level = models.ForeignKey(ClassLevel, on_delete=models.PROTECT, related_name="arms")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)

    class Meta:
        ordering = ["class_level__code", "code"]
        constraints = [
            models.UniqueConstraint(fields=["class_level", "code"], name="uq_arm_class_code")
        ]

    @property
    def institution_id(self):
        return self.class_level.institution_id

    @property
    def campus_id(self):
        return self.class_level.campus_id


class Subject(TimeStampedModel):
    institution = models.ForeignKey(
        "institutions.Institution", on_delete=models.PROTECT, related_name="subjects"
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30)

    class Meta:
        ordering = ["institution__code", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"], name="uq_subject_institution_code"
            )
        ]


class SubjectOffering(TimeStampedModel):
    session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name="subject_offerings"
    )
    term = models.ForeignKey(
        Term, on_delete=models.PROTECT, null=True, blank=True, related_name="subject_offerings"
    )
    class_level = models.ForeignKey(
        ClassLevel, on_delete=models.PROTECT, related_name="subject_offerings"
    )
    arm = models.ForeignKey(
        Arm, on_delete=models.PROTECT, null=True, blank=True, related_name="subject_offerings"
    )
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="offerings")
    is_compulsory = models.BooleanField(default=True)

    class Meta:
        ordering = ["session__code", "class_level__code", "subject__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "term", "class_level", "arm", "subject"],
                name="uq_offering_scope",
            )
        ]

    @property
    def institution_id(self):
        return self.session.institution_id

    @property
    def campus_id(self):
        return self.session.campus_id


class ClassEnrolment(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        WITHDRAWN = "withdrawn", "Withdrawn"

    session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name="enrolments"
    )
    class_level = models.ForeignKey(ClassLevel, on_delete=models.PROTECT, related_name="enrolments")
    arm = models.ForeignKey(
        Arm, on_delete=models.PROTECT, null=True, blank=True, related_name="enrolments"
    )
    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="class_enrolments"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["session__code", "class_level__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "student"], name="uq_class_enrolment_session_student"
            )
        ]

    @property
    def institution_id(self):
        return self.session.institution_id

    @property
    def campus_id(self):
        return self.session.campus_id
