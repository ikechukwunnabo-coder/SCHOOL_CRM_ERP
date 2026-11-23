import pytest
from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection

from apps.audit.models import AuditLog
from apps.audit.services import log_event, verify_audit_chain
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
    assert entry.sequence_number == 1
    assert entry.previous_hash == ""
    assert entry.entry_hash == entry.compute_entry_hash()


@pytest.mark.django_db
def test_verify_audit_chain_reports_valid_chain():
    institution = Institution.objects.create(name="Beta", code="beta")
    user = User.objects.create_user(
        email="chain@example.com", password="StrongPass123!", institution=institution
    )

    first = log_event("audit.first", actor=user)
    second = log_event("audit.second", actor=user, metadata={"ok": True})

    assert first is not None and second is not None
    result = verify_audit_chain(institution_id=institution.id)
    assert result["valid"] is True
    assert result["count"] == 2
    assert result["errors"] == []
    assert second.previous_hash == first.entry_hash


@pytest.mark.django_db
def test_verify_audit_chain_detects_tamper():
    institution = Institution.objects.create(name="Gamma", code="gamma")
    user = User.objects.create_user(
        email="tamper@example.com", password="StrongPass123!", institution=institution
    )
    entry = log_event("audit.tamper", actor=user)
    assert entry is not None

    with connection.cursor() as cursor:
        cursor.execute("DROP TRIGGER IF EXISTS audit_log_prevent_update ON audit_auditlog")
        cursor.execute(
            "UPDATE audit_auditlog SET action = %s WHERE id = %s",
            ["audit.tampered", str(entry.id)],
        )
        cursor.execute(
            """
            CREATE TRIGGER audit_log_prevent_update
            BEFORE UPDATE ON audit_auditlog
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_mutation()
            """
        )

    result = verify_audit_chain(institution_id=institution.id)
    assert result["valid"] is False
    assert any(e["error"] == "entry_hash_mismatch" for e in result["errors"])


@pytest.mark.django_db(transaction=True)
def test_audit_log_update_and_delete_blocked():
    institution = Institution.objects.create(name="Delta", code="delta")
    user = User.objects.create_user(
        email="immutable@example.com", password="StrongPass123!", institution=institution
    )
    entry = log_event("audit.immutable", actor=user)
    assert entry is not None

    with pytest.raises(DatabaseError):
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE audit_auditlog SET action = %s WHERE id = %s",
                ["audit.changed", str(entry.id)],
            )

    with pytest.raises(DatabaseError):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM audit_auditlog WHERE id = %s", [str(entry.id)])

    assert AuditLog.objects.filter(id=entry.id, action="audit.immutable").exists()


@pytest.mark.django_db
def test_log_event_does_not_block_caller_on_failure(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr("apps.audit.services.transaction.atomic", boom)

    result = log_event("audit.fail")
    assert result is None
