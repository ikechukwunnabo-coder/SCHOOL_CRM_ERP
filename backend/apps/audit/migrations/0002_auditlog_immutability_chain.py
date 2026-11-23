import hashlib
import json
import uuid

from django.db import migrations, models
from django.utils import timezone



GLOBAL_SCOPE_KEY = uuid.UUID("00000000-0000-0000-0000-000000000000")


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _hash_payload(payload):
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _chain_payload(entry):
    return {
        "id": str(entry.id),
        "sequence_number": entry.sequence_number,
        "previous_hash": entry.previous_hash or "",
        "actor_id": str(entry.actor_id) if entry.actor_id else None,
        "action": entry.action,
        "target_type": entry.target_type,
        "target_id": entry.target_id,
        "institution_id": str(entry.institution_id) if entry.institution_id else None,
        "campus_id": str(entry.campus_id) if entry.campus_id else None,
        "reason": entry.reason,
        "change_summary": entry.change_summary or {},
        "metadata": entry.metadata or {},
        "ip_address": str(entry.ip_address) if entry.ip_address else None,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


def backfill_audit_chain(apps, schema_editor):
    AuditLog = apps.get_model("audit", "AuditLog")
    entries = list(AuditLog.objects.all().order_by("created_at", "id"))
    state = {}
    for entry in entries:
        scope = entry.institution_id or GLOBAL_SCOPE_KEY
        seq, previous_hash = state.get(scope, (0, ""))
        seq += 1
        entry.sequence_number = seq
        entry.previous_hash = previous_hash
        entry.entry_hash = _hash_payload(_chain_payload(entry))
        state[scope] = (seq, entry.entry_hash)
    if entries:
        AuditLog.objects.bulk_update(entries, ["sequence_number", "previous_hash", "entry_hash"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="auditlog",
            name="sequence_number",
            field=models.PositiveBigIntegerField(null=True),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="previous_hash",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="entry_hash",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.RunPython(backfill_audit_chain, noop_reverse),
        migrations.AlterField(
            model_name="auditlog",
            name="sequence_number",
            field=models.PositiveBigIntegerField(),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="previous_hash",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="entry_hash",
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="created_at",
            field=models.DateTimeField(default=timezone.now, editable=False),
        ),
        migrations.AlterModelOptions(

            name="auditlog",
            options={"ordering": ["-created_at", "-sequence_number"]},
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["institution_id", "sequence_number"], name="audit_audit_institu_seq_idx"),
        ),
        migrations.AddConstraint(
            model_name="auditlog",
            constraint=models.UniqueConstraint(
                fields=("institution_id", "sequence_number"),
                condition=models.Q(institution_id__isnull=False),
                name="uq_audit_log_scope_sequence",
            ),
        ),
        migrations.AddConstraint(
            model_name="auditlog",
            constraint=models.UniqueConstraint(
                fields=("institution_id", "sequence_number"),
                condition=models.Q(institution_id__isnull=True),
                name="uq_audit_log_global_sequence",
            ),
        ),
        migrations.AddConstraint(
            model_name="auditlog",
            constraint=models.UniqueConstraint(
                fields=("institution_id", "entry_hash"),
                condition=models.Q(institution_id__isnull=False),
                name="uq_audit_log_scope_entry_hash",
            ),
        ),
        migrations.AddConstraint(
            model_name="auditlog",
            constraint=models.UniqueConstraint(
                fields=("institution_id", "entry_hash"),
                condition=models.Q(institution_id__isnull=True),
                name="uq_audit_log_global_entry_hash",
            ),
        ),
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'AuditLog rows are immutable';
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS audit_log_prevent_update ON audit_auditlog;
            CREATE TRIGGER audit_log_prevent_update
            BEFORE UPDATE ON audit_auditlog
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_mutation();

            DROP TRIGGER IF EXISTS audit_log_prevent_delete ON audit_auditlog;
            CREATE TRIGGER audit_log_prevent_delete
            BEFORE DELETE ON audit_auditlog
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_mutation();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS audit_log_prevent_update ON audit_auditlog;
            DROP TRIGGER IF EXISTS audit_log_prevent_delete ON audit_auditlog;
            DROP FUNCTION IF EXISTS prevent_audit_log_mutation();
            """,
        ),
    ]
