from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.core.models import TimeStampedModel
from apps.core.storage import private_document_storage


class AssessmentScheme(TimeStampedModel):
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="assessment_schemes",
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assessment_schemes",
    )
    session = models.ForeignKey(
        "app_academics.AcademicSession",
        on_delete=models.PROTECT,
        related_name="assessment_schemes",
    )
    term = models.ForeignKey(
        "app_academics.Term",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assessment_schemes",
    )
    class_level = models.ForeignKey(
        "app_academics.ClassLevel",
        on_delete=models.PROTECT,
        related_name="assessment_schemes",
    )
    arm = models.ForeignKey(
        "app_academics.Arm",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assessment_schemes",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["institution__code", "session__start_date", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="uq_assessment_scheme_institution_code",
            ),
            models.CheckConstraint(
                condition=Q(effective_to__isnull=True) | Q(effective_to__gte=F("effective_from")),
                name="ck_assessment_scheme_effective_dates",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class AssessmentComponent(TimeStampedModel):
    scheme = models.ForeignKey(
        AssessmentScheme,
        on_delete=models.CASCADE,
        related_name="components",
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=100)
    max_marks = models.DecimalField(max_digits=8, decimal_places=2)
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["scheme__code", "sequence", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["scheme", "code"],
                name="uq_assessment_component_scheme_code",
            ),
            models.CheckConstraint(
                condition=Q(max_marks__gt=0),
                name="ck_assessment_component_max_marks_positive",
            ),
            models.CheckConstraint(
                condition=Q(weight__gt=0) & Q(weight__lte=100),
                name="ck_assessment_component_weight_range",
            ),
        ]

    @property
    def institution_id(self):
        return self.scheme.institution_id

    @property
    def campus_id(self):
        return self.scheme.campus_id

    def __str__(self) -> str:
        return f"{self.scheme.code}:{self.code}"


class GradingScale(TimeStampedModel):
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="grading_scales",
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="grading_scales",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    pass_mark = models.DecimalField(max_digits=8, decimal_places=2)
    grades = models.JSONField(default=list)

    class Meta:
        ordering = ["institution__code", "-effective_from", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="uq_grading_scale_institution_code",
            ),
            models.CheckConstraint(
                condition=Q(effective_to__isnull=True) | Q(effective_to__gte=F("effective_from")),
                name="ck_grading_scale_effective_dates",
            ),
            models.CheckConstraint(
                condition=Q(pass_mark__gte=0),
                name="ck_grading_scale_pass_mark_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class GradingPolicy(TimeStampedModel):
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="grading_policies",
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="grading_policies",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    grading_scale = models.ForeignKey(
        GradingScale,
        on_delete=models.PROTECT,
        related_name="grading_policies",
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    result_completeness_rules = models.JSONField(default=dict)
    report_card_settings = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["institution__code", "-effective_from", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="uq_grading_policy_institution_code",
            ),
            models.CheckConstraint(
                condition=Q(effective_to__isnull=True) | Q(effective_to__gte=F("effective_from")),
                name="ck_grading_policy_effective_dates",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class ResultRecord(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        RETURNED = "returned", "Returned For Correction"
        APPROVED = "approved", "Approved"
        PUBLISHED = "published", "Published"

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="result_records",
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="result_records",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="result_records",
    )
    offering = models.ForeignKey(
        "app_academics.SubjectOffering",
        on_delete=models.PROTECT,
        related_name="result_records",
    )
    scheme = models.ForeignKey(
        AssessmentScheme,
        on_delete=models.PROTECT,
        related_name="result_records",
    )
    grading_scale = models.ForeignKey(
        GradingScale,
        on_delete=models.PROTECT,
        related_name="result_records",
    )
    session = models.ForeignKey(
        "app_academics.AcademicSession",
        on_delete=models.PROTECT,
        related_name="result_records",
    )
    term = models.ForeignKey(
        "app_academics.Term",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="result_records",
    )
    component_scores = models.JSONField(default=dict)
    total_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    grade = models.CharField(max_length=20, blank=True)
    remark = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    correction_count = models.PositiveIntegerField(default=0)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_results",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_results",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_results",
    )
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_results",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["institution__code", "student__admission_number", "offering__subject__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "offering", "scheme"],
                name="uq_result_record_student_offering_scheme",
            )
        ]

    def __str__(self) -> str:
        return (
            f"{self.student.admission_number}:"
            f"{self.offering.subject.code}:{self.status}"
        )


class ResultWorkflowAction(TimeStampedModel):
    result = models.ForeignKey(
        ResultRecord,
        on_delete=models.CASCADE,
        related_name="workflow_actions",
    )
    from_status = models.CharField(max_length=20, choices=ResultRecord.Status.choices)
    to_status = models.CharField(max_length=20, choices=ResultRecord.Status.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="examination_workflow_actions",
    )
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["result", "created_at", "from_status", "to_status"],
                name="uq_result_workflow_action_transition",
            )
        ]

    def __str__(self) -> str:
        return f"{self.result_id}:{self.from_status}->{self.to_status}"


class ResultCorrection(TimeStampedModel):
    result = models.ForeignKey(
        ResultRecord,
        on_delete=models.PROTECT,
        related_name="corrections",
    )
    previous_scores = models.JSONField(default=dict)
    revised_scores = models.JSONField(default=dict)
    previous_total = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    revised_total = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    previous_grade = models.CharField(max_length=20, blank=True)
    revised_grade = models.CharField(max_length=20, blank=True)
    reason = models.TextField()
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_result_corrections",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_result_corrections",
    )

    class Meta:
        ordering = ["result__student__admission_number", "-created_at"]

    def __str__(self) -> str:
        return f"Correction {self.result_id} #{self.pk}"


class ReportCard(TimeStampedModel):
    class Status(models.TextChoices):
        PUBLISHED = "published", "Published"

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="report_cards",
    )
    campus = models.ForeignKey(
        "institutions.Campus",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="report_cards",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="report_cards",
    )
    session = models.ForeignKey(
        "app_academics.AcademicSession",
        on_delete=models.PROTECT,
        related_name="report_cards",
    )
    term = models.ForeignKey(
        "app_academics.Term",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="report_cards",
    )
    reference = models.CharField(max_length=200)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    template_version = models.CharField(max_length=40, default="default-v1")
    results_snapshot = models.JSONField(default=list)
    document_snapshot = models.JSONField(default=dict)
    file = models.FileField(
        storage=private_document_storage,
        upload_to="report_cards/%Y/%m/",
        max_length=500,
        blank=True,
    )
    file_ref = models.CharField(max_length=500, blank=True)
    content_type = models.CharField(max_length=150, default="application/pdf")
    size_bytes = models.PositiveBigIntegerField(default=0)
    pdf_sha256 = models.CharField(max_length=64, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_report_cards",
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["institution__code", "student__admission_number", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "reference"],
                name="uq_report_card_institution_reference",
            )
        ]

    def __str__(self) -> str:
        return f"{self.reference} v{self.version}"
