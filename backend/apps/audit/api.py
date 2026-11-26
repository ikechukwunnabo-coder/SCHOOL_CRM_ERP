from rest_framework import serializers, viewsets

from apps.audit.models import AuditLog
from apps.permissions.permissions import (
    HasActiveInstitutionRole,
    HasInstitutionContext,
    HasModuleVerbPermission,
    IsAuthenticatedAndActive,
    IsCampusScoped,
    IsInstitutionScoped,
)


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True, default="")

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "sequence_number",
            "previous_hash",
            "entry_hash",
            "actor",
            "actor_email",
            "action",
            "target_type",
            "target_id",
            "institution_id",
            "campus_id",
            "reason",
            "change_summary",
            "metadata",
            "ip_address",
            "created_at",
        ]


BASE = [
    IsAuthenticatedAndActive,
    HasInstitutionContext,
    HasActiveInstitutionRole,
    HasModuleVerbPermission,
    IsInstitutionScoped,
    IsCampusScoped,
]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("actor").order_by("-created_at", "-sequence_number")
    serializer_class = AuditLogSerializer
    permission_classes = BASE
    module = "audit"
    verb = "view"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        qs = self.queryset
        if user.is_superuser:
            return qs
        qs = qs.filter(institution_id=user.institution_id)
        if getattr(user, "campus_id", None):
            qs = qs.filter(campus_id=user.campus_id) | qs.filter(campus_id__isnull=True)
        return qs
