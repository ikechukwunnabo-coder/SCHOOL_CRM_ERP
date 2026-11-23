import hashlib
import json
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sequence_number = models.PositiveBigIntegerField()
    previous_hash = models.CharField(max_length=64, blank=True)
    entry_hash = models.CharField(max_length=64)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=150)
    target_type = models.CharField(max_length=150, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    institution_id = models.UUIDField(null=True, blank=True)
    campus_id = models.UUIDField(null=True, blank=True)
    reason = models.TextField(blank=True)
    change_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at", "-sequence_number"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["institution_id", "created_at"]),
            models.Index(
                fields=["institution_id", "sequence_number"],
                name="audit_audit_institu_seq_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["institution_id", "sequence_number"],
                condition=Q(institution_id__isnull=False),
                name="uq_audit_log_scope_sequence",
            ),
            models.UniqueConstraint(
                fields=["institution_id", "sequence_number"],
                condition=Q(institution_id__isnull=True),
                name="uq_audit_log_global_sequence",
            ),
            models.UniqueConstraint(
                fields=["institution_id", "entry_hash"],
                condition=Q(institution_id__isnull=False),
                name="uq_audit_log_scope_entry_hash",
            ),
            models.UniqueConstraint(
                fields=["institution_id", "entry_hash"],
                condition=Q(institution_id__isnull=True),
                name="uq_audit_log_global_entry_hash",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {self.action}"

    @staticmethod
    def _canonical_json(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)

    @classmethod
    def hash_payload(cls, payload: dict) -> str:
        return hashlib.sha256(cls._canonical_json(payload).encode("utf-8")).hexdigest()

    def chain_payload(self) -> dict:
        created_at = self.created_at
        if created_at is not None:
            if timezone.is_naive(created_at):
                created_at = timezone.make_aware(created_at, timezone.get_current_timezone())
            created_at = created_at.isoformat()
        return {
            "id": str(self.id),
            "sequence_number": self.sequence_number,
            "previous_hash": self.previous_hash,
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "institution_id": str(self.institution_id) if self.institution_id else None,
            "campus_id": str(self.campus_id) if self.campus_id else None,
            "reason": self.reason,
            "change_summary": self.change_summary or {},
            "metadata": self.metadata or {},
            "ip_address": self.ip_address,
            "created_at": created_at,
        }

    def compute_entry_hash(self) -> str:
        return self.hash_payload(self.chain_payload())
