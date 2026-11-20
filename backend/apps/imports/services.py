from __future__ import annotations

import csv
import io
from datetime import date

from django.db import IntegrityError, transaction

from apps.audit.services import log_event
from apps.core.identifiers import generate_identifier
from apps.students.models import STUDENT_GENDER_VALUES, Student, build_identity_key

from .models import ImportJob, ImportRowError

TEMPLATE_HEADERS = [
    "admission_number",
    "first_name",
    "last_name",
    "date_of_birth",
    "gender",
    "admission_date",
]


class ImportErrorValue(ValueError):
    pass


def template_csv() -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TEMPLATE_HEADERS)
    writer.writeheader()
    writer.writerow(
        {
            "admission_number": "ADM-2026-000001",
            "first_name": "Example",
            "last_name": "Student",
            "date_of_birth": "2015-01-01",
            "gender": "unspecified",
            "admission_date": "2026-01-15",
        }
    )
    return output.getvalue()


def create_job(actor, *, institution, campus=None, dataset, source_name, dry_run=True) -> ImportJob:
    job = ImportJob.objects.create(
        institution=institution,
        campus=campus,
        dataset=dataset,
        source_name=source_name,
        dry_run=dry_run,
        created_by=actor,
        mapping={"fields": TEMPLATE_HEADERS},
    )
    log_event(
        "imports.job_created",
        actor=actor,
        target_type="imports.ImportJob",
        target_id=job.pk,
        institution_id=institution.id,
        campus_id=getattr(campus, "id", None),
        change_summary={"dataset": dataset, "source_name": source_name},
    )
    return job


def _parse_rows(payload: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(payload))
    if not reader.fieldnames or not set(TEMPLATE_HEADERS).issubset(reader.fieldnames):
        raise ImportErrorValue("invalid_template")
    return [dict(row) for row in reader]


def _validate(job: ImportJob, rows: list[dict]) -> tuple[list[dict], list[dict]]:
    valid: list[dict] = []
    errors: list[dict] = []
    seen: set[str] = set()
    existing = set(
        Student.objects.filter(institution_id=job.institution_id).values_list(
            "identity_key", flat=True
        )
    )
    for index, row in enumerate(rows, start=2):
        row_errors: list[dict] = []
        identity = ""
        try:
            date_of_birth = date.fromisoformat(row["date_of_birth"].strip())
            admission_date = date.fromisoformat(row["admission_date"].strip())
        except (ValueError, AttributeError, KeyError):
            row_errors.append({"field": "date_of_birth", "message": "invalid_date"})
            date_of_birth = None
            admission_date = date.today()
        first_name = (row.get("first_name") or "").strip()
        last_name = (row.get("last_name") or "").strip()
        if not first_name or not last_name:
            row_errors.append({"field": "name", "message": "required"})
        gender = (row.get("gender") or "unspecified").strip().lower()
        if gender not in STUDENT_GENDER_VALUES:
            row_errors.append({"field": "gender", "message": "invalid_gender"})
        if date_of_birth is not None:
            identity = build_identity_key(first_name, last_name, date_of_birth)
        if identity and (identity in existing or identity in seen):
            row_errors.append({"field": "identity", "message": "duplicate_identity"})
        if identity:
            seen.add(identity)
        if row_errors:
            errors.append({"row_number": index, "errors": row_errors, "raw_data": row})
        else:
            valid.append(
                {
                    "admission_number": row["admission_number"].strip(),
                    "first_name": first_name,
                    "last_name": last_name,
                    "date_of_birth": date_of_birth,
                    "gender": gender,
                    "admission_date": admission_date,
                }
            )
    return valid, errors


def _store_errors(job: ImportJob, errors: list[dict]) -> None:
    job.row_errors.all().delete()
    for error in errors:
        for item in error["errors"]:
            ImportRowError.objects.create(
                job=job,
                row_number=error["row_number"],
                field=item["field"],
                message=item["message"],
                raw_data=error["raw_data"],
            )


def preview_job(actor, job: ImportJob, payload: str) -> ImportJob:
    rows = _parse_rows(payload)
    valid, errors = _validate(job, rows)
    job.payload = payload
    job.summary = {
        "total_rows": len(rows),
        "valid_rows": len(valid),
        "error_rows": len(errors),
        "dry_run": job.dry_run,
    }
    job.status = ImportJob.Status.PREVIEWED
    job.save(update_fields=["payload", "summary", "status", "updated_at"])
    _store_errors(job, errors)
    log_event(
        "imports.previewed",
        actor=actor,
        target_type="imports.ImportJob",
        target_id=job.pk,
        institution_id=job.institution_id,
        campus_id=job.campus_id,
        change_summary=job.summary,
    )
    return job


def approve_job(actor, job: ImportJob) -> ImportJob:
    if job.status != ImportJob.Status.PREVIEWED:
        raise ImportErrorValue("invalid_import_state")
    job.status = ImportJob.Status.APPROVED
    job.approved_by = actor
    job.save(update_fields=["status", "approved_by", "updated_at"])
    log_event(
        "imports.approved",
        actor=actor,
        target_type="imports.ImportJob",
        target_id=job.pk,
        institution_id=job.institution_id,
        campus_id=job.campus_id,
    )
    return job


def apply_job(actor, job: ImportJob) -> ImportJob:
    if job.status != ImportJob.Status.APPROVED:
        raise ImportErrorValue("invalid_import_state")
    valid, errors = _validate(job, _parse_rows(job.payload))
    if errors:
        raise ImportErrorValue("import_has_row_errors")
    created = 0
    try:
        with transaction.atomic():
            year = date.today().year
            for row in valid:
                Student.objects.create(
                    institution_id=job.institution_id,
                    campus_id=job.campus_id,
                    admission_number=generate_identifier(
                        job.institution,
                        "admission_number",
                        year=year,
                        scope=str(year),
                    ),
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    date_of_birth=row["date_of_birth"],
                    gender=row["gender"],
                    admission_date=row["admission_date"],
                    status=Student.LifecycleStatus.ADMITTED,
                )
                created += 1
            job.status = ImportJob.Status.APPLIED
            job.summary = {**job.summary, "applied_rows": created, "source_refs": [job.source_name]}
            job.save(update_fields=["status", "summary", "updated_at"])
    except IntegrityError as exc:
        job.status = ImportJob.Status.FAILED
        job.save(update_fields=["status", "updated_at"])
        raise ImportErrorValue("import_failed") from exc
    log_event(
        "imports.executed",
        actor=actor,
        target_type="imports.ImportJob",
        target_id=job.pk,
        institution_id=job.institution_id,
        campus_id=job.campus_id,
        change_summary=job.summary,
    )
    return job
