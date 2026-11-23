from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.academics.models import ClassEnrolment
from apps.audit.services import log_event
from apps.permissions.services import get_user_role_names, user_has_module_permission
from apps.teaching.services import resolve_teacher_scope

from .models import (
    AssessmentComponent,
    AssessmentScheme,
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
    if getattr(obj, "institution_id", None) != getattr(actor, "institution_id", None):
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
    if "Teacher" in roles:
        assignments = resolve_teacher_scope(actor)
        if any(assignment.offering_id == offering.pk for assignment in assignments):
            return
        raise ExaminationError("teacher_not_assigned_to_offering")
    if user_has_module_permission(actor, "examinations", "create"):
        return
    raise ExaminationError("entry_not_permitted")


def select_grading_scale(*, institution_id, campus_id=None, as_of=None):
    effective_date = as_of or timezone.localdate()
    queryset = GradingScale.objects.filter(
        institution_id=institution_id,
        effective_from__lte=effective_date,
    ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=effective_date))
    if campus_id is not None:
        queryset = queryset.filter(Q(campus_id__isnull=True) | Q(campus_id=campus_id))
    else:
        queryset = queryset.filter(campus_id__isnull=True)
    scale = queryset.order_by("-effective_from", "-created_at").first()
    if scale is None:
        raise ExaminationError("grading_scale_not_found")
    return scale


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


def _calculate_scores(component_scores, components, scale: GradingScale):
    if not isinstance(component_scores, dict):
        raise ExaminationError("invalid_component_scores")
    expected_codes = {component.code for component in components}
    if set(component_scores) != expected_codes:
        raise ExaminationError("component_scores_mismatch")
    normalised = {}
    total = Decimal("0")
    for component in components:
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
    scale = select_grading_scale(
        institution_id=scheme.institution_id,
        campus_id=scheme.campus_id,
        as_of=timezone.localdate(),
    )
    normalised, total, grade, remark = _calculate_scores(component_scores, components, scale)
    with transaction.atomic():
        result, _ = ResultRecord.objects.update_or_create(
            student=student,
            offering=offering,
            scheme=scheme,
            defaults={
                "institution": scheme.institution,
                "campus": scheme.campus,
                "grading_scale": scale,
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
    normalised, total, grade, remark = _calculate_scores(
        component_scores, components, result.grading_scale
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
    results = ResultRecord.objects.filter(
        student=student,
        session=session,
        status=ResultRecord.Status.PUBLISHED,
    ).select_related("offering__subject")
    if term is not None:
        results = results.filter(term=term)
    snapshot = [
        {
            "offering_code": result.offering.subject.code,
            "subject": result.offering.subject.name,
            "total_score": str(result.total_score),
            "grade": result.grade,
            "remark": result.remark,
        }
        for result in results.order_by("offering__subject__code")
    ]
    if not snapshot:
        raise ExaminationError("no_published_results")
    term_code = term.code if term is not None else "SESSION"
    reference = f"RC-{student.admission_number}-{session.code}-{term_code}"
    defaults = {
        "campus": student.campus,
        "template_version": "default-v1",
        "results_snapshot": snapshot,
        "generated_by": actor,
        "published_at": timezone.now(),
    }
    with transaction.atomic():
        card, created = ReportCard.objects.get_or_create(
            institution=session.institution,
            reference=reference,
            defaults={**defaults, "student": student, "session": session, "term": term},
        )
        if not created:
            card.student = student
            card.session = session
            card.term = term
            card.version += 1
            for key, value in defaults.items():
                setattr(card, key, value)
            card.save(
                update_fields=[
                    "student",
                    "session",
                    "term",
                    "version",
                    "template_version",
                    "results_snapshot",
                    "generated_by",
                    "published_at",
                    "updated_at",
                ]
            )
    _audit(actor, "examinations.report_card_generated", card)
    return card
