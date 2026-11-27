import csv

from django.db.models import Count
from django.http import HttpResponse
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import ConflictError
from apps.permissions.permissions import (
    HasActiveInstitutionRole,
    HasInstitutionContext,
    HasModuleVerbPermission,
    IsAuthenticatedAndActive,
    IsCampusScoped,
    IsInstitutionScoped,
)

from .models import Notification, NotificationTemplate
from .services import NotificationError, send_notification


def serializer_for(model_class):
    class Serializer(serializers.ModelSerializer):
        class Meta:
            model = model_class
            fields = "__all__"
            read_only_fields = ["id", "created_at", "updated_at"]

    Serializer.__name__ = f"{model_class.__name__}Serializer"
    return Serializer


BASE = [
    IsAuthenticatedAndActive,
    HasInstitutionContext,
    HasActiveInstitutionRole,
    HasModuleVerbPermission,
    IsInstitutionScoped,
    IsCampusScoped,
]


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.select_related("institution")
    serializer_class = serializer_for(NotificationTemplate)
    permission_classes = BASE
    module = "notifications"
    verb = "view"
    verb_map = {
        "create": "create",
        "update": "update",
        "partial_update": "update",
        "destroy": "delete_or_archive",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        qs = self.queryset
        if user.is_superuser:
            return qs
        return qs.filter(institution_id=user.institution_id)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_superuser:
            serializer.save(institution=user.institution)
        else:
            serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        if not user.is_superuser:
            serializer.save(institution=user.institution)
        else:
            serializer.save()


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Notification.objects.select_related("institution", "campus", "recipient_user")
    serializer_class = serializer_for(Notification)
    permission_classes = BASE
    module = "notifications"
    verb = "view"
    verb_map = {"send": "update"}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        qs = self.queryset
        if user.is_superuser:
            return qs
        qs = qs.filter(institution_id=user.institution_id)
        if getattr(user, "campus_id", None):
            qs = qs.filter(campus_id=user.campus_id) | qs.filter(campus__isnull=True)
        return qs

    @action(detail=True, methods=["post"])
    def send(self, request, *args, **kwargs):
        notification = self.get_object()
        try:
            notification = send_notification(actor=request.user, notification=notification)
        except NotificationError as exc:
            raise ConflictError(detail=str(exc)) from exc
        return Response(self.get_serializer(notification).data, status=status.HTTP_200_OK)


class NotificationDashboardViewSet(viewsets.ViewSet):
    permission_classes = BASE
    module = "notifications"
    verb = "view"
    verb_map = {"export_logs": "export"}

    def _scoped_qs(self, request):
        user = request.user
        qs = Notification.objects.all()
        if not user.is_superuser:
            qs = qs.filter(institution_id=user.institution_id)
            if getattr(user, "campus_id", None):
                qs = qs.filter(campus_id=user.campus_id) | qs.filter(campus__isnull=True)
        return qs

    def list(self, request):
        qs = self._scoped_qs(request)
        return Response(
            {
                "count": qs.count(),
                "unread_count": qs.exclude(status=Notification.Status.READ).count(),
                "by_status": {
                    row["status"]: row["c"] for row in qs.values("status").annotate(c=Count("id"))
                },
                "by_channel": {
                    row["channel"]: row["c"]
                    for row in qs.values("channel").annotate(c=Count("id"))
                },
            }
        )

    @action(detail=False, methods=["get"], url_path="export-logs")
    def export_logs(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="notification-logs.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "id",
                "created_at",
                "channel",
                "status",
                "recipient_email",
                "recipient_phone",
                "subject",
            ]
        )
        for row in self._scoped_qs(request).order_by("-created_at")[:5000]:
            writer.writerow(
                [
                    row.id,
                    row.created_at.isoformat() if row.created_at else "",
                    row.channel,
                    row.status,
                    row.recipient_email,
                    row.recipient_phone,
                    row.subject,
                ]
            )
        return response
