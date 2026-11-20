from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import storages

ALLOWED_DOCUMENT_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def private_document_storage():
    return storages["private_documents"]


def safe_document_name(original_name: str) -> str:
    suffix = Path(original_name or "").suffix.lower()
    if suffix not in ALLOWED_DOCUMENT_TYPES:
        raise ValueError("unsupported_file_type")
    return f"{uuid.uuid4().hex}{suffix}"


def scan_document(uploaded, storage_name: str) -> str:
    hook = getattr(settings, "DOCUMENT_MALWARE_SCAN_HOOK", "")
    if not hook:
        return "not_configured"
    module_name, _, function_name = hook.rpartition(".")
    module = __import__(module_name, fromlist=[function_name])
    return getattr(module, function_name)(uploaded, storage_name) or "clean"


def prepare_document_upload(uploaded) -> tuple[str, str, int]:
    name = safe_document_name(uploaded.name)
    suffix = Path(uploaded.name).suffix.lower()
    expected = ALLOWED_DOCUMENT_TYPES[suffix]
    content_type = (getattr(uploaded, "content_type", "") or "").split(";")[0].strip().lower()
    if content_type and content_type != expected:
        raise ValueError("content_type_mismatch")
    if uploaded.size > settings.DOCUMENT_UPLOAD_MAX_BYTES:
        raise ValueError("file_too_large")
    return name, content_type or expected, uploaded.size
