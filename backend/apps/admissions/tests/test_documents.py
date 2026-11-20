import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.admissions.tests.test_workflow import prepare_accepted_application, setup_school
from apps.audit.models import AuditLog

PDF = b"%PDF-1.4\ntest\n%%EOF"


@pytest.mark.django_db
def test_private_document_upload_download_and_scope_denial():
    institution, campus, registrar = setup_school("docs")
    application = prepare_accepted_application(institution, campus, registrar)
    client = APIClient()
    client.force_login(registrar)

    upload = client.post(
        f"/api/v1/admissions/applications/{application.id}/upload_document/",
        {
            "checklist_item": "Birth certificate",
            "file": SimpleUploadedFile("birth.pdf", PDF, content_type="application/pdf"),
        },
        format="multipart",
    )
    assert upload.status_code == 201, upload.data
    document_id = upload.data["id"]

    download = client.get(f"/api/v1/admissions/application-documents/{document_id}/download/")
    assert download.status_code == 200
    assert download["Content-Type"] == "application/pdf"

    invalid = client.post(
        f"/api/v1/admissions/applications/{application.id}/upload_document/",
        {
            "checklist_item": "Bad file",
            "file": SimpleUploadedFile("bad.exe", b"MZ", content_type="application/octet-stream"),
        },
        format="multipart",
    )
    assert invalid.status_code == 400

    other_institution, _, other_user = setup_school("docother")
    other_client = APIClient()
    other_client.force_login(other_user)
    assert other_client.get(
        f"/api/v1/admissions/application-documents/{document_id}/download/"
    ).status_code == 404

    assert AuditLog.objects.filter(action="documents.uploaded").exists()
    assert AuditLog.objects.filter(action="documents.downloaded").exists()
