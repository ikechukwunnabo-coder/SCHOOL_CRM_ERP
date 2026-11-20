import pytest
from django.contrib.auth import get_user_model

from apps.audit.services import log_event
from apps.institutions.models import Institution

User = get_user_model()


@pytest.mark.django_db
def test_log_event_redacts_secrets_and_derives_scope():
    institution = Institution.objects.create(name="Alpha", code="alpha")
    user = User.objects.create_user(
        email="audit@example.com", password="StrongPass123!", institution=institution
    )

    entry = log_event(
        "audit.test",
        actor=user,
        target_type="accounts.User",
        target_id="x" * 100,
        metadata={"password": "secret", "nested": {"token": "abc"}, "safe": "ok"},
        change_summary={"api_key": "hidden", "name": "Alpha"},
    )

    assert entry is not None
    assert entry.institution_id == institution.id
    assert len(entry.target_id) == 64
    assert entry.metadata["password"] == "[REDACTED]"
    assert entry.metadata["nested"]["token"] == "[REDACTED]"
    assert entry.metadata["safe"] == "ok"
    assert entry.change_summary["api_key"] == "[REDACTED]"
    assert entry.change_summary["name"] == "Alpha"
