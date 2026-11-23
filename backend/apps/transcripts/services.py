from __future__ import annotations

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.academics.models import ClassEnrolment
from apps.audit.services import log_event
from apps.core.document_generation import (
    generated_pdf_filename,
    hash_verification_token,
    new_verification_token,
    render_transcript_pdf,
    sha256_bytes,
    verification_path,
)
from apps.core.identifiers import generate_identifier
from apps.examinations.models import ResultRecord
from apps.students.models import Student, StudentLifecycleEvent

from .models import (
    Transcript,
    TranscriptEvent,
    TranscriptKind,
    TranscriptRequest,
    TranscriptVerification,
)


class TranscriptError(Exception):
    pass


def ensure_institution_scope(actor, *, institution_id, campus_id=None):
    if institution_id is None:
        return
    if not getattr(actor, "is_authenticated", False):
        raise TranscriptError("authentication_required")
    if getattr(actor, "is_superuser", False):
        return
    if getattr(actor, "institution_id", None) != institution_id:
        raise TranscriptError("cross_institution_access_denied")
    actor_campus_id = getattr(actor, "campus_id", None)
    if campus_id and actor_campus_id and actor_campus_id != campus_id:
        raise TranscriptError("cross_campus_access_denied")


def ensure_entry_scope(actor, entry):
    ensure_institution_scope(
        actor,
        institution_id=entry.institution_id,
        campus_id=entry.campus_id,
    )


def _audit(action, *, actor, target, reason="", metadata=None):
    log_event(
        action,
        actor=actor,
        target_type=target.__class__.__name__,
        target_id=str(target.pk),
        institution_id=getattr(target, "institution_id", None),
        campus_id=getattr(target, "campus_id", None),
        reason=reason,
        metadata=metadata,
    )


def _record_event(
    action,
    *,
    actor,
    request=None,
    transcript=None,
    from_status="",
    to_status="",
    reason="",
):
    return TranscriptEvent.objects.create(
        request=request,
        transcript=transcript,
        action=action,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        reason=reason,
    )


@transaction.atomic
def request_transcript(actor, *, student: Student, purpose: str, requested_kind: str):
    if not purpose.strip():
        raise TranscriptError("transcript_purpose_required")
    if requested_kind not in TranscriptKind.values:
        raise TranscriptError("invalid_transcript_kind")
    ensure_institution_scope(
        actor,
        institution_id=student.institution_id,
        campus_id=student.campus_id,
    )
    request_obj = TranscriptRequest.objects.create(
        institution=student.institution,
        campus=student.campus,
        student=student,
        requested_by=actor if getattr(actor, "is_authenticated", False) else None,
        purpose=purpose,
        requested_kind=requested_kind,
    )
    _record_event(
        "requested",
        actor=actor,
        request=request_obj,
        to_status=TranscriptRequest.Status.REQUESTED,
    )
    _audit("transcripts.request_created", actor=actor, target=request_obj)
    return request_obj


@transaction.atomic
def review_transcript_request(actor, *, request, reason=""):
    request_obj = TranscriptRequest.objects.select_for_update().get(pk=request.pk)
    ensure_entry_scope(actor, request_obj)
    if request_obj.status not in {
        TranscriptRequest.Status.REQUESTED,
        TranscriptRequest.Status.UNDER_REVIEW,
    }:
        raise TranscriptError("transcript_request_not_reviewable")
    old_status = request_obj.status
    request_obj.status = TranscriptRequest.Status.UNDER_REVIEW
    request_obj.reviewed_by = actor if getattr(actor, "is_authenticated", False) else None
    request_obj.reviewed_at = timezone.now()
    request_obj.decision_reason = reason
    request_obj.save(
        update_fields=["status", "reviewed_by", "reviewed_at", "decision_reason", "updated_at"]
    )
    _record_event(
        "reviewed",
        actor=actor,
        request=request_obj,
        from_status=old_status,
        to_status=request_obj.status,
        reason=reason,
    )
    _audit("transcripts.request_reviewed", actor=actor, target=request_obj, reason=reason)
    return request_obj


@transaction.atomic
def approve_transcript_request(actor, *, request, reason=""):
    request_obj = TranscriptRequest.objects.select_for_update().get(pk=request.pk)
    ensure_entry_scope(actor, request_obj)
    if request_obj.status not in {
        TranscriptRequest.Status.REQUESTED,
        TranscriptRequest.Status.UNDER_REVIEW,
    }:
        raise TranscriptError("transcript_request_not_approvable")
    if (
        request_obj.requested_by_id
        and getattr(actor, "id", None) == request_obj.requested_by_id
        and not getattr(actor, "is_superuser", False)
    ):
        raise TranscriptError("transcript_request_self_approval_denied")
    old_status = request_obj.status
    request_obj.status = TranscriptRequest.Status.APPROVED
    request_obj.approved_by = actor if getattr(actor, "is_authenticated", False) else None
    request_obj.approved_at = timezone.now()
    request_obj.decision_reason = reason
    request_obj.save(
        update_fields=["status", "approved_by", "approved_at", "decision_reason", "updated_at"]
    )
    _record_event(
        "approved",
        actor=actor,
        request=request_obj,
        from_status=old_status,
        to_status=request_obj.status,
        reason=reason,
    )
    _audit("transcripts.request_approved", actor=actor, target=request_obj, reason=reason)
    return request_obj


@transaction.atomic
def reject_transcript_request(actor, *, request, reason):
    if not reason.strip():
        raise TranscriptError("transcript_rejection_reason_required")
    request_obj = TranscriptRequest.objects.select_for_update().get(pk=request.pk)
    ensure_entry_scope(actor, request_obj)
    if request_obj.status not in {
        TranscriptRequest.Status.REQUESTED,
        TranscriptRequest.Status.UNDER_REVIEW,
    }:
        raise TranscriptError("transcript_request_not_rejectable")
    old_status = request_obj.status
    request_obj.status = TranscriptRequest.Status.REJECTED
    request_obj.reviewed_by = actor if getattr(actor, "is_authenticated", False) else None
    request_obj.reviewed_at = timezone.now()
    request_obj.decision_reason = reason
    request_obj.save(
        update_fields=["status", "reviewed_by", "reviewed_at", "decision_reason", "updated_at"]
    )
    _record_event(
        "rejected",
        actor=actor,
        request=request_obj,
        from_status=old_status,
        to_status=request_obj.status,
        reason=reason,
    )
    _audit("transcripts.request_rejected", actor=actor, target=request_obj, reason=reason)
    return request_obj


def build_transcript_snapshot(request_obj: TranscriptRequest):
    student = request_obj.student
    results = list(
        ResultRecord.objects.filter(student=student, status=ResultRecord.Status.PUBLISHED)
        .select_related(
            "session",
            "term",
            "offering__subject",
            "offering__class_level",
            "offering__arm",
            "scheme",
            "grading_scale",
        )
        .order_by("session__start_date", "term__start_date", "offering__subject__code")
    )
    enrolled_sessions = list(
        ClassEnrolment.objects.filter(student=student)
        .exclude(status=ClassEnrolment.Status.WITHDRAWN)
        .values_list("session_id", "session__code")
    )
    published_session_ids = {result.session_id for result in results}
    missing_sessions = sorted(
        code for session_id, code in enrolled_sessions if session_id not in published_session_ids
    )
    unpublished_results = [
        {
            "id": str(result.id),
            "status": result.status,
            "session": result.session.code,
            "subject": result.offering.subject.code,
        }
        for result in ResultRecord.objects.filter(student=student)
        .exclude(status=ResultRecord.Status.PUBLISHED)
        .select_related("session", "offering__subject")
    ]
    graduation_event = (
        StudentLifecycleEvent.objects.filter(
            student=student,
            to_status=Student.LifecycleStatus.GRADUATED,
        )
        .order_by("-created_at")
        .first()
    )
    completeness = {
        "published_result_count": len(results),
        "missing_sessions": missing_sessions,
        "unpublished_results": unpublished_results,
        "has_graduation_record": graduation_event is not None,
        "is_complete": bool(results)
        and not missing_sessions
        and not unpublished_results
        and graduation_event is not None,
    }
    graduation_date = (
        graduation_event.effective_date.isoformat() if graduation_event is not None else ""
    )
    document = {
        "institution": {
            "id": str(request_obj.institution_id),
            "name": request_obj.institution.name,
            "code": request_obj.institution.code,
        },
        "student": {
            "id": str(student.id),
            "full_name": student.full_name,
            "admission_number": student.admission_number,
            "admission_date": student.admission_date.isoformat(),
            "graduation_date": graduation_date,
        },
        "request": {
            "id": str(request_obj.id),
            "purpose": request_obj.purpose,
            "requested_kind": request_obj.requested_kind,
        },
        "completeness": completeness,
    }
    results_snapshot = [
        {
            "session": {
                "id": str(result.session_id),
                "code": result.session.code,
                "name": result.session.name,
                "end_date": result.session.end_date.isoformat(),
            },
            "term": (
                {
                    "id": str(result.term_id),
                    "code": result.term.code,
                    "name": result.term.name,
                }
                if result.term_id
                else None
            ),
            "class_level": {
                "id": str(result.offering.class_level_id),
                "code": result.offering.class_level.code,
                "name": result.offering.class_level.name,
            },
            "arm": (
                {
                    "id": str(result.offering.arm_id),
                    "code": result.offering.arm.code,
                    "name": result.offering.arm.name,
                }
                if result.offering.arm_id
                else None
            ),
            "subject": {
                "id": str(result.offering.subject_id),
                "code": result.offering.subject.code,
                "name": result.offering.subject.name,
            },
            "scheme": {
                "id": str(result.scheme_id),
                "code": result.scheme.code,
                "name": result.scheme.name,
            },
            "grading_scale": {
                "id": str(result.grading_scale_id),
                "code": result.grading_scale.code,
                "name": result.grading_scale.name,
                "grades": result.grading_scale.grades,
            },
            "component_scores": result.component_scores,
            "total_score": str(result.total_score) if result.total_score is not None else "",
            "grade": result.grade,
            "remark": result.remark,
        }
        for result in results
    ]
    return document, results_snapshot, completeness


@transaction.atomic
def generate_transcript(actor, *, request):
    request_obj = TranscriptRequest.objects.select_for_update().get(pk=request.pk)
    ensure_entry_scope(actor, request_obj)
    if request_obj.status != TranscriptRequest.Status.APPROVED:
        raise TranscriptError("transcript_request_not_approved")
    document, results_snapshot, completeness = build_transcript_snapshot(request_obj)
    institution_settings = request_obj.institution.settings or {}
    if (
        request_obj.requested_kind == TranscriptKind.OFFICIAL
        and not completeness["is_complete"]
        and institution_settings.get("transcript_block_incomplete_official", True)
    ):
        raise TranscriptError("official_transcript_requires_complete_record")
    kind = (
        TranscriptKind.OFFICIAL
        if completeness["is_complete"] and request_obj.requested_kind == TranscriptKind.OFFICIAL
        else TranscriptKind.PROVISIONAL
    )
    raw_token, token_hash = new_verification_token()
    reference = generate_identifier(
        request_obj.institution,
        "transcript_reference",
        year=timezone.localdate().year,
    )
    document.update(
        {
            "reference_number": reference,
            "version": 1,
            "kind": kind,
            "template_version": "default-v1",
            "issued_at": "",
        }
    )
    pdf_bytes = render_transcript_pdf(
        document=document,
        results=results_snapshot,
        verification_url=verification_path(raw_token),
    )
    transcript = Transcript.objects.create(
        institution=request_obj.institution,
        campus=request_obj.campus,
        student=request_obj.student,
        request=request_obj,
        reference_number=reference,
        version=1,
        kind=kind,
        status=Transcript.Status.GENERATED,
        verification_token_hash=token_hash,
        template_version="default-v1",
        approved_by=request_obj.approved_by,
        document_snapshot=document,
        results_snapshot=results_snapshot,
        completeness=completeness,
    )
    filename = generated_pdf_filename(reference, transcript.version)
    transcript.file.save(filename, ContentFile(pdf_bytes), save=False)
    transcript.file_ref = transcript.file.name
    transcript.size_bytes = len(pdf_bytes)
    transcript.pdf_sha256 = sha256_bytes(pdf_bytes)
    transcript.save()
    old_status = request_obj.status
    request_obj.status = TranscriptRequest.Status.GENERATED
    request_obj.save(update_fields=["status", "updated_at"])
    _record_event(
        "generated",
        actor=actor,
        request=request_obj,
        transcript=transcript,
        from_status=old_status,
        to_status=Transcript.Status.GENERATED,
    )
    _audit("transcripts.generated", actor=actor, target=transcript)
    return transcript, raw_token


@transaction.atomic
def issue_transcript(actor, *, transcript, issued_to: str, purpose: str):
    transcript_obj = Transcript.objects.select_for_update().get(pk=transcript.pk)
    ensure_entry_scope(actor, transcript_obj)
    if transcript_obj.status != Transcript.Status.GENERATED:
        raise TranscriptError("transcript_not_issuable")
    if not issued_to.strip():
        raise TranscriptError("transcript_issued_to_required")
    old_status = transcript_obj.status
    transcript_obj.status = Transcript.Status.ISSUED
    transcript_obj.issued_to = issued_to
    transcript_obj.issue_purpose = purpose
    transcript_obj.issued_by = actor if getattr(actor, "is_authenticated", False) else None
    transcript_obj.issued_at = timezone.now()
    transcript_obj.save(
        update_fields=[
            "status",
            "issued_to",
            "issue_purpose",
            "issued_by",
            "issued_at",
            "updated_at",
        ]
    )
    request_obj = transcript_obj.request
    request_obj.status = TranscriptRequest.Status.ISSUED
    request_obj.save(update_fields=["status", "updated_at"])
    _record_event(
        "issued",
        actor=actor,
        request=request_obj,
        transcript=transcript_obj,
        from_status=old_status,
        to_status=Transcript.Status.ISSUED,
        reason=purpose,
    )
    _audit("transcripts.issued", actor=actor, target=transcript_obj, reason=purpose)
    return transcript_obj


@transaction.atomic
def correct_transcript(actor, *, transcript, reason, issued_to="", purpose=""):
    if not reason.strip():
        raise TranscriptError("transcript_correction_reason_required")
    old = Transcript.objects.select_for_update().get(pk=transcript.pk)
    ensure_entry_scope(actor, old)
    if old.status != Transcript.Status.ISSUED:
        raise TranscriptError("transcript_not_correctable")
    raw_token, token_hash = new_verification_token()
    reference = generate_identifier(
        old.institution,
        "transcript_reference",
        year=timezone.localdate().year,
    )
    version = old.version + 1
    document = dict(old.document_snapshot)
    document.update(
        {
            "reference_number": reference,
            "version": version,
            "kind": old.kind,
            "template_version": old.template_version,
            "issued_at": "",
        }
    )
    pdf_bytes = render_transcript_pdf(
        document=document,
        results=old.results_snapshot,
        verification_url=verification_path(raw_token),
    )
    new = Transcript.objects.create(
        institution=old.institution,
        campus=old.campus,
        student=old.student,
        request=old.request,
        supersedes=old,
        reference_number=reference,
        version=version,
        kind=old.kind,
        status=Transcript.Status.GENERATED,
        verification_token_hash=token_hash,
        template_version=old.template_version,
        approved_by=old.approved_by,
        issued_to=issued_to or old.issued_to,
        issue_purpose=purpose or old.issue_purpose,
        document_snapshot=document,
        results_snapshot=old.results_snapshot,
        completeness=old.completeness,
    )
    filename = generated_pdf_filename(reference, version)
    new.file.save(filename, ContentFile(pdf_bytes), save=False)
    new.file_ref = new.file.name
    new.size_bytes = len(pdf_bytes)
    new.pdf_sha256 = sha256_bytes(pdf_bytes)
    new.save()
    old_status = old.status
    old.status = Transcript.Status.SUPERSEDED
    old.save(update_fields=["status", "updated_at"])
    request_obj = old.request
    request_obj.status = TranscriptRequest.Status.GENERATED
    request_obj.save(update_fields=["status", "updated_at"])
    _record_event(
        "superseded",
        actor=actor,
        request=request_obj,
        transcript=old,
        from_status=old_status,
        to_status=Transcript.Status.SUPERSEDED,
        reason=reason,
    )
    _record_event(
        "corrected",
        actor=actor,
        request=request_obj,
        transcript=new,
        from_status=old_status,
        to_status=Transcript.Status.GENERATED,
        reason=reason,
    )
    _audit("transcripts.corrected", actor=actor, target=new, reason=reason)
    return new, raw_token


@transaction.atomic
def revoke_transcript(actor, *, transcript, reason):
    if not reason.strip():
        raise TranscriptError("transcript_revocation_reason_required")
    transcript_obj = Transcript.objects.select_for_update().get(pk=transcript.pk)
    ensure_entry_scope(actor, transcript_obj)
    if transcript_obj.status not in {Transcript.Status.GENERATED, Transcript.Status.ISSUED}:
        raise TranscriptError("transcript_not_revocable")
    old_status = transcript_obj.status
    transcript_obj.status = Transcript.Status.REVOKED
    transcript_obj.verification_revoked_at = timezone.now()
    transcript_obj.save(update_fields=["status", "verification_revoked_at", "updated_at"])
    _record_event(
        "revoked",
        actor=actor,
        request=transcript_obj.request,
        transcript=transcript_obj,
        from_status=old_status,
        to_status=Transcript.Status.REVOKED,
        reason=reason,
    )
    _audit("transcripts.revoked", actor=actor, target=transcript_obj, reason=reason)
    return transcript_obj


def verify_transcript(raw_token: str):
    token_hash = hash_verification_token(raw_token)
    transcript = (
        Transcript.objects.filter(verification_token_hash=token_hash)
        .select_related("institution")
        .first()
    )
    if transcript is None:
        outcome = TranscriptVerification.Outcome.INVALID
    elif transcript.status == Transcript.Status.REVOKED:
        outcome = TranscriptVerification.Outcome.REVOKED
    elif transcript.status in {Transcript.Status.SUPERSEDED, Transcript.Status.CORRECTED}:
        outcome = TranscriptVerification.Outcome.SUPERSEDED
    elif transcript.status != Transcript.Status.ISSUED:
        outcome = TranscriptVerification.Outcome.INVALID_STATE
    else:
        outcome = TranscriptVerification.Outcome.VALID
    verification = TranscriptVerification.objects.create(
        transcript=transcript,
        token_hash=token_hash,
        outcome=outcome,
    )
    log_event(
        "transcripts.verification_checked",
        actor=None,
        target_type="TranscriptVerification",
        target_id=str(verification.id),
        institution_id=transcript.institution_id if transcript else None,
        campus_id=transcript.campus_id if transcript else None,
        metadata={"outcome": outcome},
    )
    response = {
        "valid": outcome == TranscriptVerification.Outcome.VALID,
        "status": outcome,
        "checked_at": verification.checked_at.isoformat(),
    }
    if transcript is not None:
        response.update(
            {
                "institution": {
                    "name": transcript.institution.name,
                    "code": transcript.institution.code,
                },
                "reference_number": transcript.reference_number,
                "version": transcript.version,
                "kind": transcript.kind,
                "issued_at": transcript.issued_at.isoformat() if transcript.issued_at else None,
            }
        )
    return response


@transaction.atomic
def prepare_transcript_download(actor, *, transcript):
    transcript_obj = Transcript.objects.select_related("institution", "campus").get(
        pk=transcript.pk
    )
    ensure_entry_scope(actor, transcript_obj)
    if transcript_obj.status != Transcript.Status.ISSUED:
        raise TranscriptError("transcript_not_downloadable")
    if not transcript_obj.file:
        raise TranscriptError("transcript_file_missing")
    _audit("transcripts.downloaded", actor=actor, target=transcript_obj)
    return transcript_obj.file
