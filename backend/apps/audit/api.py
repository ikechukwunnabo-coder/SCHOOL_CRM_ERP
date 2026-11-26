import csv

from django.http import HttpResponse
from rest_framework import serializers, viewsets
from rest_framework.decorators import action

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
    verb_map = {"export_csv": "export"}

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

    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit-logs.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "id",
                "created_at",
                "actor_email",
                "action",
                "target_type",
                "target_id",
                "institution_id",
                "campus_id",
                "reason",
            ]
        )
        for row in self.get_queryset()[:5000]:
            writer.writerow(
                [
                    row.id,
                    row.created_at.isoformat() if row.created_at else "",
                    row.actor.email if row.actor_id else "",
                    row.action,
                    row.target_type,
                    row.target_id,
                    row.institution_id,
                    row.campus_id,
                    row.reason,
                ]
            )
        return response
