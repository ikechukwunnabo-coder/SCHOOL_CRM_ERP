from django.db import transaction

from apps.audit.services import log_event

from .models import AlumniRecord


class AlumniError(ValueError):
    pass


def ensure_institution_scope(actor, obj) -> None:
    if actor is None or getattr(actor, "is_superuser", False):
        return
    if getattr(obj, "institution_id", None) != getattr(actor, "institution_id", None):
        raise AlumniError("institution_scope_violation")
    campus_id = getattr(obj, "campus_id", None)
    actor_campus_id = getattr(actor, "campus_id", None)
    if campus_id is not None and actor_campus_id not in (None, campus_id):
        raise AlumniError("campus_scope_violation")


def sync_alumni_record(*, actor, student, event=None) -> AlumniRecord:
    ensure_institution_scope(actor, student)
    graduation_date = getattr(event, "effective_date", None) or getattr(
        student, "admission_date", None
    )
    if graduation_date is None:
        raise AlumniError("graduation_date_required")
    with transaction.atomic():
        record, created = AlumniRecord.objects.get_or_create(
            institution=student.institution,
            student=student,
            defaults={
                "campus": student.campus,
                "graduation_event": event,
                "graduation_date": graduation_date,
                "graduation_reference": f"AL-{student.admission_number}",
            },
        )
        if not created:
            update_fields = []
            for field, value in {
                "campus": student.campus,
                "graduation_event": event or record.graduation_event,
                "graduation_date": graduation_date,
                "graduation_reference": record.graduation_reference
                or f"AL-{student.admission_number}",
            }.items():
                if getattr(record, field) != value:
                    setattr(record, field, value)
                    update_fields.append(field)
            if update_fields:
                record.save(update_fields=[*update_fields, "updated_at"])
    if created:
        log_event(
            "alumni.record_created",
            actor=actor,
            target_type="alumni.AlumniRecord",
            target_id=record.pk,
            institution_id=record.institution_id,
            campus_id=record.campus_id,
        )
    return record
