import pytest

from apps.admissions.tests.test_workflow import setup_school
from apps.audit.models import AuditLog
from apps.imports.models import ImportJob
from apps.imports.services import (
    ImportErrorValue,
    apply_job,
    approve_job,
    create_job,
    preview_job,
    template_csv,
)
from apps.students.models import Student

VALID = """admission_number,first_name,last_name,date_of_birth,gender,admission_date
ADM-2026-000010,Ada,Okafor,2015-04-01,female,2026-01-15
"""


@pytest.mark.django_db
def test_import_preview_duplicate_detection_and_atomic_apply():
    institution, campus, registrar = setup_school("imports")
    assert "date_of_birth" in template_csv()

    job = create_job(
        registrar,
        institution=institution,
        campus=campus,
        dataset=ImportJob.Dataset.STUDENTS,
        source_name="students.csv",
        dry_run=True,
    )
    preview_job(registrar, job, VALID)
    assert job.summary["valid_rows"] == 1
    assert job.summary["error_rows"] == 0
    approve_job(registrar, job)
    apply_job(registrar, job)
    assert job.status == ImportJob.Status.APPLIED
    assert Student.objects.count() == 1

    duplicate = VALID.replace("ADM-2026-000010", "ADM-2026-000011")
    second = create_job(
        registrar,
        institution=institution,
        campus=campus,
        dataset=ImportJob.Dataset.STUDENTS,
        source_name="duplicate.csv",
    )
    preview_job(registrar, second, duplicate)
    assert second.summary["error_rows"] == 1
    assert second.row_errors.filter(message="duplicate_identity").exists()
    approve_job(registrar, second)
    with pytest.raises(ImportErrorValue):
        apply_job(registrar, second)
    assert Student.objects.count() == 1
    assert AuditLog.objects.filter(action="imports.executed").count() == 1
