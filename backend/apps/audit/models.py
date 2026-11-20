import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Immutable-style audit record for sensitive operations (foundation)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["institution_id", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {self.action}"
