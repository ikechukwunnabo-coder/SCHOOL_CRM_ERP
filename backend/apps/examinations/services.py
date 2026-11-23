from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.academics.models import ClassEnrolment
from apps.audit.services import log_event
from apps.core.document_generation import sha256_bytes
from apps.permissions.roles import SUBJECT_TEACHER
from apps.permissions.services import get_user_role_names, user_has_module_permission
from apps.teaching.services import resolve_teacher_scope

from .models import (
    AssessmentComponent,
    AssessmentScheme,
    GradingPolicy,
    GradingScale,
    ReportCard,
    ResultCorrection,
    ResultRecord,
    ResultWorkflowAction,
)


class ExaminationError(ValueError):
    pass


def _actor_label(actor) -> str:
    if actor is None:
        return "system"
    return getattr(actor, "email", None) or getattr(actor, "username", "") or str(actor.pk)


def _audit(actor, action: str, target, **kwargs) -> None:
    log_event(
        action,
        actor=actor,
        target_type=type(target).__name__,
        target_id=getattr(target, "pk", ""),
        institution_id=kwargs.pop("institution_id", getattr(target, "institution_id", None)),
        campus_id=kwargs.pop("campus_id", getattr(target, "campus_id", None)),
        **kwargs,
    )


def _as_decimal(value, code: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ExaminationError(f"invalid_{code}") from None


def ensure_institution_scope(actor, obj) -> None:
    if actor is None or getattr(actor, "is_superuser", False):
        return
    obj_institution_id = getattr(obj, "institution_id", None)
    model_label = getattr(getattr(obj, "_meta", None), "label", "")
    if obj_institution_id is None and model_label.lower() == "institutions.institution":
        obj_institution_id = obj.pk
    if obj_institution_id != getattr(actor, "institution_id", None):
        raise ExaminationError("institution_scope_violation")
    campus_id = getattr(obj, "campus_id", None)
    actor_campus_id = getattr(actor, "campus_id", None)
    if campus_id is not None and actor_campus_id not in (None, campus_id):
        raise ExaminationError("campus_scope_violation")


def ensure_entry_scope(actor, offering) -> None:
    ensure_institution_scope(actor, offering)
    if actor is None or getattr(actor, "is_superuser", False):
        return
    roles = set(get_user_role_names(actor))
    if SUBJECT_TEACHER in roles:
        assignments = resolve_teacher_scope(actor)
        if any(assignment.offering_id == offering.pk for assignment in assignments):
            return
        raise ExaminationError("teacher_not_assigned_to_offering")
    if user_has_module_permission(actor, "examinations", "create"):
        return
    raise ExaminationError("entry_not_permitted")


DEFAULT_GRADING_SCALE_GRADES = [
    {"min": "70", "max": "100", "grade": "A", "remark": "Excellent"},
    {"min": "60", "max": "69.99", "grade": "B", "remark": "Very Good"},
    {"min": "50", "max": "59.99", "grade": "C", "remark": "Good"},
    {"min": "45", "max": "49.99", "grade": "D", "remark": "Pass"},
    {"min": "0", "max": "44.99", "grade": "F", "remark": "Fail"},
]
DEFAULT_RESULT_COMPLETENESS_RULES = {
    "require_all_components": True,
    "require_published_results_for_report_card": True,
}
DEFAULT_REPORT_CARD_SETTINGS = {
    "template_version": "default-v1",
    "include_component_scores": False,
}


def default_grading_policy_payload():
    grades = getattr(settings, "EXAMINATIONS_DEFAULT_GRADING_SCALE_GRADES", None)
    if grades is None:
        grades = DEFAULT_GRADING_SCALE_GRADES
    completeness = getattr(settings, "EXAMINATIONS_DEFAULT_RESULT_COMPLETENESS_RULES", None)
    if completeness is None:
        completeness = DEFAULT_RESULT_COMPLETENESS_RULES
    report_card = getattr(settings, "EXAMINATIONS_DEFAULT_REPORT_CARD_SETTINGS", None)
    if report_card is None:
        report_card = DEFAULT_REPORT_CARD_SETTINGS
    return {
        "grading_scale_code": getattr(
            settings, "EXAMINATIONS_DEFAULT_GRADING_SCALE_CODE", "DEFAULT"
        ),
        "grading_scale_name": getattr(
            settings, "EXAMINATIONS_DEFAULT_GRADING_SCALE_NAME", "Default Grading Scale"
        ),
        "pass_mark": str(getattr(settings, "EXAMINATIONS_DEFAULT_PASS_MARK", "50")),
        "grades": grades,
        "policy_code": getattr(settings, "EXAMINATIONS_DEFAULT_GRADING_POLICY_CODE", "DEFAULT"),
        "policy_name": getattr(
            settings, "EXAMINATIONS_DEFAULT_GRADING_POLICY_NAME", "Default Grading Policy"
        ),
        "result_completeness_rules": completeness,
        "report_card_settings": report_card,
    }


def _normalize_grading_scale_payload(*, grades, pass_mark):
    if not isinstance(grades, list) or not grades:
        raise ExaminationError("invalid_grading_scale")
    ranges = []
    normalized_grades = []
    for entry in grades:
        if not isinstance(entry, dict):
            raise ExaminationError("invalid_grading_scale")
        minimum = _as_decimal(entry.get("min"), "grade_min")
        maximum = _as_decimal(entry.get("max"), "grade_max")
        grade = str(entry.get("grade", "")).strip()
        if minimum > maximum or not grade:
            raise ExaminationError("invalid_grading_scale")
        ranges.append((minimum, maximum))
        normalized_grades.append(
            {
                "min": str(minimum),
                "max": str(maximum),
                "grade": grade,
                "remark": str(entry.get("remark", "")).strip(),
            }
        )
    ranges.sort(key=lambda item: item[0])
    for previous, current in zip(ranges, ranges[1:], strict=False):
        if current[0] <= previous[1]:
            raise ExaminationError("overlapping_grade_ranges")
    pass_mark_value = _as_decimal(pass_mark, "pass_mark")
    if not any(minimum <= pass_mark_value <= maximum for minimum, maximum in ranges):
        raise ExaminationError("pass_mark_outside_grade_ranges")
    return normalized_grades, pass_mark_value


def _effective_queryset(queryset, *, effective_date, campus_id=None):
    queryset = queryset.filter(effective_from__lte=effective_date).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=effective_date)
    )
    if campus_id is not None:
        queryset = queryset.filter(Q(campus_id__isnull=True) | Q(campus_id=campus_id)).order_by(
            "-effective_from", "-created_at"
        )
    else:
        queryset = queryset.filter(campus_id__isnull=True).order_by(
            "-effective_from", "-created_at"
        )
    return queryset


def ensure_default_grading_policy(*, institution, campus=None, as_of=None):
    effective_date = as_of or timezone.localdate()
    existing = _effective_queryset(
        GradingPolicy.objects.filter(institution=institution, is_active=True),
        effective_date=effective_date,
        campus_id=campus.pk if campus else None,
    ).first()
    if existing is not None:
        return existing
    defaults = default_grading_policy_payload()
    grades, pass_mark = _normalize_grading_scale_payload(
        grades=defaults["grades"], pass_mark=defaults["pass_mark"]
    )
    scale = GradingScale.objects.filter(
        institution=institution,
        code=str(defaults["grading_scale_code"]).strip().upper(),
    ).first()
    if scale is None:
        scale = GradingScale.objects.create(
            institution=institution,
            campus=campus,
            name=str(defaults["grading_scale_name"]).strip(),
            code=str(defaults["grading_scale_code"]).strip().upper(),
            effective_from=effective_date,
            pass_mark=pass_mark,
            grades=grades,
        )
    return GradingPolicy.objects.create(
        institution=institution,
        campus=campus,
        name=str(defaults["policy_name"]).strip(),
        code=str(defaults["policy_code"]).strip().upper(),
        grading_scale=scale,
        effective_from=effective_date,
        result_completeness_rules=dict(defaults["result_completeness_rules"]),
        report_card_settings=dict(defaults["report_card_settings"]),
    )


def select_grading_policy(*, institution, campus=None, as_of=None):
    effective_date = as_of or timezone.localdate()
    policy = _effective_queryset(
        GradingPolicy.objects.select_related("grading_scale").filter(
            institution=institution, is_active=True
        ),
        effective_date=effective_date,
        campus_id=campus.pk if campus else None,
    ).first()
    if policy is None:
        policy = ensure_default_grading_policy(
            institution=institution, campus=campus, as_of=effective_date
        )
    return policy


def select_grading_scale(*, institution_id, campus_id=None, as_of=None):
    from apps.institutions.models import Campus, Institution

    institution = Institution.objects.filter(pk=institution_id).first()
    if institution is None:
        raise ExaminationError("grading_scale_not_found")
    campus = Campus.objects.filter(pk=campus_id).first() if campus_id else None
    policy = select_grading_policy(institution=institution, campus=campus, as_of=as_of)
    return policy.grading_scale


def create_scheme(
    actor,
    *,
    institution,
    campus=None,
    session,
    term=None,
    class_level,
    arm=None,
    name: str,
    code: str,
    effective_from,
    effective_to=None,
) -> AssessmentScheme:
    if institution.pk != session.institution_id:
        raise ExaminationError("session_institution_mismatch")
    if institution.pk != class_level.institution_id:
        raise ExaminationError("class_level_institution_mismatch")
    if campus is not None:
        if campus.institution_id != institution.pk:
            raise ExaminationError("campus_institution_mismatch")
        if session.campus_id is not None and session.campus_id != campus.pk:
            raise ExaminationError("session_campus_mismatch")
    if term is not None and term.session_id != session.pk:
        raise ExaminationError("term_session_mismatch")
    if arm is not None and arm.institution_id != institution.pk:
        raise ExaminationError("arm_institution_mismatch")
    if effective_to is not None and effective_to < effective_from:
        raise ExaminationError("invalid_effective_dates")
    scheme = AssessmentScheme.objects.create(
        institution=institution,
        campus=campus,
        session=session,
        term=term,
        class_level=class_level,
        arm=arm,
        name=name.strip(),
        code=code.strip().upper(),
        effective_from=effective_from,
        effective_to=effective_to,
    )
    _audit(actor, "examinations.scheme_created", scheme)
    return scheme


def add_component(
    actor,
    *,
    scheme: AssessmentScheme,
    code: str,
    name: str,
    max_marks,
    weight,
    sequence: int = 0,
) -> AssessmentComponent:
    ensure_institution_scope(actor, scheme)
    max_marks_value = _as_decimal(max_marks, "max_marks")
    weight_value = _as_decimal(weight, "weight")
    if max_marks_value <= 0:
        raise ExaminationError("invalid_max_marks")
    if weight_value <= 0 or weight_value > 100:
        raise ExaminationError("invalid_weight")
    component = AssessmentComponent.objects.create(
        scheme=scheme,
        code=code.strip().upper(),
        name=name.strip(),
        max_marks=max_marks_value,
        weight=weight_value,
        sequence=sequence,
    )
    _audit(actor, "examinations.component_added", component)
    return component


def create_grading_scale(
    actor,
    *,
    institution,
    campus=None,
    name: str,
    code: str,
    effective_from,
    effective_to=None,
    grades,
    pass_mark,
) -> GradingScale:
    if campus is not None and campus.institution_id != institution.pk:
        raise ExaminationError("campus_institution_mismatch")
    if effective_to is not None and effective_to < effective_from:
        raise ExaminationError("invalid_effective_dates")
    normalized_grades, pass_mark_value = _normalize_grading_scale_payload(
        grades=grades, pass_mark=pass_mark
    )
    scale = GradingScale.objects.create(
        institution=institution,
        campus=campus,
        name=name.strip(),
        code=code.strip().upper(),
        effective_from=effective_from,
        effective_to=effective_to,
        pass_mark=pass_mark_value,
        grades=normalized_grades,
    )
    _audit(actor, "examinations.grading_scale_created", scale)
    return scale


def create_grading_policy(
    actor,
    *,
    institution,
    campus=None,
    grading_scale: GradingScale,
    name: str,
    code: str,
    effective_from,
    effective_to=None,
    result_completeness_rules=None,
    report_card_settings=None,
    is_active=True,
) -> GradingPolicy:
    ensure_institution_scope(actor, institution)
    if grading_scale.institution_id != institution.pk:
        raise ExaminationError("grading_scale_institution_mismatch")
    if campus is not None and campus.institution_id != institution.pk:
        raise ExaminationError("campus_institution_mismatch")
    if effective_to is not None and effective_to < effective_from:
        raise ExaminationError("invalid_effective_dates")
    completeness = dict(default_grading_policy_payload()["result_completeness_rules"])
    if isinstance(result_completeness_rules, dict):
        completeness.update(result_completeness_rules)
    report_settings = dict(default_grading_policy_payload()["report_card_settings"])
    if isinstance(report_card_settings, dict):
        report_settings.update(report_card_settings)
    policy = GradingPolicy.objects.create(
        institution=institution,
        campus=campus,
        grading_scale=grading_scale,
        name=name.strip(),
        code=code.strip().upper(),
        effective_from=effective_from,
        effective_to=effective_to,
        result_completeness_rules=completeness,
        report_card_settings=report_settings,
        is_active=is_active,
    )
    _audit(actor, "examinations.grading_policy_created", policy)
    return policy


def validate_scheme(scheme: AssessmentScheme) -> list[AssessmentComponent]:
    if not scheme.is_active:
        raise ExaminationError("scheme_inactive")
    components = list(scheme.components.all())
    if not components:
        raise ExaminationError("scheme_has_no_components")
    if sum((component.weight for component in components), Decimal("0")) != Decimal("100"):
        raise ExaminationError("component_weights_must_total_100")
    return components


def expected_students(scheme: AssessmentScheme):
    queryset = ClassEnrolment.objects.filter(
        session=scheme.session,
        class_level=scheme.class_level,
        status=ClassEnrolment.Status.ACTIVE,
    )
    if scheme.arm_id is not None:
        queryset = queryset.filter(arm=scheme.arm)
    return queryset.select_related("student")


def _calculate_scores(
    component_scores, components, scale: GradingScale, *, completeness_rules=None
):
    if not isinstance(component_scores, dict):
        raise ExaminationError("invalid_component_scores")
    rules = dict(default_grading_policy_payload()["result_completeness_rules"])
    if isinstance(completeness_rules, dict):
        rules.update(completeness_rules)
    expected_codes = {component.code for component in components}
    if rules.get("require_all_components", True):
        if set(component_scores) != expected_codes:
            raise ExaminationError("component_scores_mismatch")
    else:
        unknown = set(component_scores) - expected_codes
        if unknown:
            raise ExaminationError("unknown_component_scores")
        if not component_scores:
            raise ExaminationError("component_scores_mismatch")
    normalised = {}
    total = Decimal("0")
    for component in components:
        if component.code not in component_scores:
            continue
        value = _as_decimal(component_scores.get(component.code), "score")
        if value < 0 or value > component.max_marks:
            raise ExaminationError("score_out_of_range")
        normalised[component.code] = str(value)
        total += value * component.weight / Decimal("100")
    total = total.quantize(Decimal("0.01"))
    grade_entry = None
    for entry in sorted(scale.grades, key=lambda item: _as_decimal(item.get("min"), "grade_min")):
        minimum = _as_decimal(entry.get("min"), "grade_min")
        maximum = _as_decimal(entry.get("max"), "grade_max")
        if minimum <= total <= maximum:
            grade_entry = entry
            break
    if grade_entry is None:
        raise ExaminationError("grade_scale_gap")
    grade = str(grade_entry.get("grade", "")).strip()
    remark = str(grade_entry.get("remark", "")).strip()
    if not remark:
        remark = "Pass" if total >= scale.pass_mark else "Fail"
    return normalised, total, grade, remark


def record_result(
    actor,
    *,
    scheme: AssessmentScheme,
    offering,
    student,
    component_scores,
) -> ResultRecord:
    ensure_institution_scope(actor, scheme)
    ensure_institution_scope(actor, offering)
    ensure_entry_scope(actor, offering)
    components = validate_scheme(scheme)
    if scheme.session_id != offering.session_id:
        raise ExaminationError("offering_session_mismatch")
    if scheme.term_id is not None and scheme.term_id != offering.term_id:
        raise ExaminationError("offering_term_mismatch")
    if scheme.class_level_id != offering.class_level_id:
        raise ExaminationError("offering_class_level_mismatch")
    if scheme.arm_id is not None and scheme.arm_id != offering.arm_id:
        raise ExaminationError("offering_arm_mismatch")
    if not expected_students(scheme).filter(student_id=student.pk).exists():
        raise ExaminationError("student_not_enrolled_for_scheme")
    policy = select_grading_policy(
        institution=scheme.institution,
        campus=scheme.campus,
        as_of=timezone.localdate(),
    )
    normalised, total, grade, remark = _calculate_scores(
        component_scores,
        components,
        policy.grading_scale,
        completeness_rules=policy.result_completeness_rules,
    )
    with transaction.atomic():
        result, _ = ResultRecord.objects.update_or_create(
            student=student,
            offering=offering,
            scheme=scheme,
            defaults={
                "institution": scheme.institution,
                "campus": scheme.campus,
                "grading_scale": policy.grading_scale,
                "session": scheme.session,
                "term": scheme.term,
                "component_scores": normalised,
                "total_score": total,
                "grade": grade,
                "remark": remark,
                "status": ResultRecord.Status.DRAFT,
            },
        )
    _audit(actor, "examinations.result_recorded", result)
    return result


def submit_results(actor, *, scheme: AssessmentScheme, offering) -> int:
    ensure_institution_scope(actor, scheme)
    ensure_entry_scope(actor, offering)
    components = validate_scheme(scheme)
    if scheme.session_id != offering.session_id:
        raise ExaminationError("offering_session_mismatch")
    if scheme.class_level_id != offering.class_level_id:
        raise ExaminationError("offering_class_level_mismatch")
    expected_ids = list(expected_students(scheme).values_list("student_id", flat=True))
    submit_time = timezone.now()
    submitted = 0
    with transaction.atomic():
        records = list(
            ResultRecord.objects.filter(scheme=scheme, offering=offering).select_for_update()
        )
        recorded_ids = {result.student_id for result in records}
        if set(expected_ids) != recorded_ids:
            raise ExaminationError("not_all_students_recorded")
        for result in records:
            if result.status not in {
                ResultRecord.Status.DRAFT,
                ResultRecord.Status.RETURNED,
            }:
                raise ExaminationError("result_not_submittable")
            previous_status = result.status
            result.status = ResultRecord.Status.SUBMITTED
            result.submitted_by = actor
            result.submitted_at = submit_time
            result.save(
                update_fields=["status", "submitted_by", "submitted_at", "updated_at"]
            )
            ResultWorkflowAction.objects.create(
                result=result,
                from_status=previous_status,
                to_status=ResultRecord.Status.SUBMITTED,
                actor=actor,
            )
            submitted += 1
    _audit(
        actor,
        "examinations.results_submitted",
        scheme,
        change_summary={"offering_id": str(offering.pk), "count": submitted},
        metadata={"components": [component.code for component in components]},
    )
    return submitted


def return_for_correction(actor, *, result: ResultRecord, reason: str) -> ResultRecord:
    ensure_institution_scope(actor, result)
    if not reason.strip():
        raise ExaminationError("reason_required")
    if result.status != ResultRecord.Status.SUBMITTED:
        raise ExaminationError("result_not_submitted")
    previous_status = result.status
    result.status = ResultRecord.Status.RETURNED
    result.reviewed_by = actor
    result.reviewed_at = timezone.now()
    with transaction.atomic():
        result.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        ResultWorkflowAction.objects.create(
            result=result,
            from_status=previous_status,
            to_status=ResultRecord.Status.RETURNED,
            actor=actor,
            reason=reason.strip(),
        )
    _audit(actor, "examinations.result_returned", result, reason=reason.strip())
    return result


def approve_result(actor, *, result: ResultRecord) -> ResultRecord:
    ensure_institution_scope(actor, result)
    if result.status != ResultRecord.Status.SUBMITTED:
        raise ExaminationError("result_not_submitted")
    if actor is not None and not actor.is_superuser and result.submitted_by_id == actor.pk:
        raise ExaminationError("self_approval_not_permitted")
    previous_status = result.status
    result.status = ResultRecord.Status.APPROVED
    result.approved_by = actor
    result.approved_at = timezone.now()
    with transaction.atomic():
        result.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        ResultWorkflowAction.objects.create(
            result=result,
            from_status=previous_status,
            to_status=ResultRecord.Status.APPROVED,
            actor=actor,
        )
    _audit(actor, "examinations.result_approved", result)
    return result


def publish_result(actor, *, result: ResultRecord) -> ResultRecord:
    ensure_institution_scope(actor, result)
    if result.status != ResultRecord.Status.APPROVED:
        raise ExaminationError("result_not_approved")
    previous_status = result.status
    result.status = ResultRecord.Status.PUBLISHED
    result.published_by = actor
    result.published_at = timezone.now()
    with transaction.atomic():
        result.save(update_fields=["status", "published_by", "published_at", "updated_at"])
        ResultWorkflowAction.objects.create(
            result=result,
            from_status=previous_status,
            to_status=ResultRecord.Status.PUBLISHED,
            actor=actor,
        )
    _audit(actor, "examinations.result_published", result)
    return result


def correct_result(
    actor,
    *,
    result: ResultRecord,
    component_scores,
    reason: str,
) -> ResultRecord:
    ensure_institution_scope(actor, result)
    if not reason.strip():
        raise ExaminationError("reason_required")
    if result.status not in {ResultRecord.Status.APPROVED, ResultRecord.Status.PUBLISHED}:
        raise ExaminationError("result_not_correctable")
    components = validate_scheme(result.scheme)
    policy = select_grading_policy(
        institution=result.institution,
        campus=result.campus,
        as_of=timezone.localdate(),
    )
    normalised, total, grade, remark = _calculate_scores(
        component_scores,
        components,
        result.grading_scale,
        completeness_rules=policy.result_completeness_rules,
    )
    previous_status = result.status
    with transaction.atomic():
        ResultCorrection.objects.create(
            result=result,
            previous_scores=result.component_scores,
            revised_scores=normalised,
            previous_total=result.total_score,
            revised_total=total,
            previous_grade=result.grade,
            revised_grade=grade,
            reason=reason.strip(),
            requested_by=actor,
        )
        result.component_scores = normalised
        result.total_score = total
        result.grade = grade
        result.remark = remark
        result.status = ResultRecord.Status.SUBMITTED
        result.submitted_by = actor
        result.submitted_at = timezone.now()
        result.correction_count += 1
        result.save(
            update_fields=[
                "component_scores",
                "total_score",
                "grade",
                "remark",
                "status",
                "submitted_by",
                "submitted_at",
                "correction_count",
                "updated_at",
            ]
        )
        ResultWorkflowAction.objects.create(
            result=result,
            from_status=previous_status,
            to_status=ResultRecord.Status.SUBMITTED,
            actor=actor,
            reason=reason.strip(),
        )
    _audit(actor, "examinations.result_corrected", result, reason=reason.strip())
    return result


def _report_card_filename(reference: str, version: int) -> str:
    safe_reference = "".join(char for char in reference if char.isalnum() or char in "-_.")
    return f"report_cards/{safe_reference or 'report-card'}-v{version}.pdf"


def _report_card_snapshot(*, student, session, term, results, policy):
    return {
        "institution": {
            "id": str(session.institution_id),
            "name": session.institution.name,
            "code": session.institution.code,
        },
        "student": {
            "id": str(student.id),
            "full_name": student.full_name,
            "admission_number": student.admission_number,
        },
        "session": {"id": str(session.id), "code": session.code, "name": session.name},
        "term": (
            {"id": str(term.id), "code": term.code, "name": term.name} if term is not None else None
        ),
        "policy": {
            "id": str(policy.id),
            "code": policy.code,
            "grading_scale_code": policy.grading_scale.code,
        },
        "results": [
            {
                "offering_code": result.offering.subject.code,
                "subject": result.offering.subject.name,
                "total_score": str(result.total_score),
                "grade": result.grade,
                "remark": result.remark,
                "component_scores": result.component_scores,
            }
            for result in results
        ],
    }


def render_report_card_pdf(*, document: dict) -> bytes:
    from io import BytesIO
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"Report Card {document.get('reference', '')}",
        author=str(document.get("institution", {}).get("name", "")),
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "ReportCardHeading",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=16,
        spaceAfter=4,
    )
    subheading = ParagraphStyle(
        "ReportCardSubheading",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=9,
        textColor=colors.HexColor("#555555"),
        spaceAfter=10,
    )
    section = ParagraphStyle(
        "ReportCardSection",
        parent=styles["Heading2"],
        fontSize=11,
        spaceBefore=8,
        spaceAfter=4,
    )
    small = ParagraphStyle("ReportCardSmall", parent=styles["Normal"], fontSize=8, leading=10)
    institution = document.get("institution", {})
    student = document.get("student", {})
    session = document.get("session", {})
    term = document.get("term") or {}
    story = [
        Paragraph(escape(str(institution.get("name", ""))), heading),
        Paragraph(escape(str(institution.get("code", ""))), subheading),
        Paragraph("Report Card", heading),
        Paragraph(
            escape(
                f"Reference: {document.get('reference', '')} | "
                f"Version: {document.get('version', '')}"
            ),
            subheading,
        ),
        Paragraph("Student details", section),
        Table(
            [
                ["Student", escape(str(student.get("full_name", "")))],
                ["Admission number", escape(str(student.get("admission_number", "")))],
                ["Session", escape(str(session.get("name", session.get("code", ""))))],
                ["Term", escape(str(term.get("name", term.get("code", "Session"))))],
            ],
            colWidths=[38 * mm, 140 * mm],
        ),
        Paragraph("Results", section),
    ]
    rows = [["Subject", "Code", "Total", "Grade", "Remark"]]
    for result in document.get("results", []):
        rows.append(
            [
                escape(str(result.get("subject", ""))),
                escape(str(result.get("offering_code", ""))),
                escape(str(result.get("total_score", ""))),
                escape(str(result.get("grade", ""))),
                escape(str(result.get("remark", ""))),
            ]
        )
    table = Table(rows, colWidths=[58 * mm, 22 * mm, 20 * mm, 18 * mm, 60 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#AAAAAA")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            escape(
                "Generated from published result snapshots. "
                f"Template: {document.get('template_version', '')}"
            ),
            small,
        )
    )
    doc.build(story)
    return buffer.getvalue()


def generate_report_card(
    actor,
    *,
    student,
    session,
    term=None,
) -> ReportCard:
    ensure_institution_scope(actor, session)
    if student.institution_id != session.institution_id:
        raise ExaminationError("student_session_institution_mismatch")
    if term is not None and term.session_id != session.pk:
        raise ExaminationError("term_session_mismatch")
    policy = select_grading_policy(
        institution=session.institution,
        campus=student.campus or session.campus,
        as_of=timezone.localdate(),
    )
    results = ResultRecord.objects.filter(
        student=student,
        session=session,
        status=ResultRecord.Status.PUBLISHED,
    ).select_related("offering__subject")
    if term is not None:
        results = results.filter(term=term)
    results = list(results.order_by("offering__subject__code"))
    if not results:
        raise ExaminationError("no_published_results")
    term_code = term.code if term is not None else "SESSION"
    reference = f"RC-{student.admission_number}-{session.code}-{term_code}"
    template_version = str(policy.report_card_settings.get("template_version", "default-v1"))
    snapshot = _report_card_snapshot(
        student=student, session=session, term=term, results=results, policy=policy
    )
    with transaction.atomic():
        card, created = ReportCard.objects.get_or_create(
            institution=session.institution,
            reference=reference,
            defaults={
                "student": student,
                "campus": student.campus,
                "session": session,
                "term": term,
                "template_version": template_version,
                "results_snapshot": snapshot["results"],
                "document_snapshot": snapshot,
                "generated_by": actor,
                "published_at": timezone.now(),
            },
        )
        if not created:
            card.student = student
            card.campus = student.campus
            card.session = session
            card.term = term
            card.version += 1
            card.template_version = template_version
            card.results_snapshot = snapshot["results"]
            card.document_snapshot = snapshot
            card.generated_by = actor
            card.published_at = timezone.now()
        document = dict(snapshot)
        document.update(
            {
                "reference": reference,
                "version": card.version,
                "template_version": template_version,
            }
        )
        card.document_snapshot = document
        pdf_bytes = render_report_card_pdf(document=document)
        card.file.save(
            _report_card_filename(reference, card.version), ContentFile(pdf_bytes), save=False
        )
        card.file_ref = card.file.name
        card.content_type = "application/pdf"
        card.size_bytes = len(pdf_bytes)
        card.pdf_sha256 = sha256_bytes(pdf_bytes)
        card.save()
    _audit(actor, "examinations.report_card_generated", card)
    return card


def prepare_report_card_download(actor, *, report_card: ReportCard):
    card = ReportCard.objects.select_related("institution", "student", "session", "term").get(
        pk=report_card.pk
    )
    ensure_institution_scope(actor, card)
    if card.status != ReportCard.Status.PUBLISHED:
        raise ExaminationError("report_card_not_downloadable")
    if not card.file:
        raise ExaminationError("report_card_file_missing")
    _audit(actor, "examinations.report_card_downloaded", card)
    return card.file
