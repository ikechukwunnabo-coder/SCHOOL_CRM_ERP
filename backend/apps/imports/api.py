from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
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
from apps.permissions.services import user_can_access_campus_id, user_can_access_institution

from . import services
from .models import ImportJob

BASE_PERMISSIONS = [
    IsAuthenticatedAndActive,
    HasInstitutionContext,
    HasActiveInstitutionRole,
    HasModuleVerbPermission,
    IsInstitutionScoped,
    IsCampusScoped,
]


class ImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportJob
        fields = [
            "id", "institution", "campus", "dataset", "status", "source_name",
            "source_ref", "dry_run", "mapping", "summary", "created_at",
        ]
        read_only_fields = fields


class PreviewSerializer(serializers.Serializer):
    payload = serializers.CharField()


class ImportJobViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ImportJobSerializer
    permission_classes = BASE_PERMISSIONS
    queryset = ImportJob.objects.all()
    module = "imports"
    verb = "view"
    verb_map = {
        "create_job": "create",
        "preview": "create",
        "approve": "approve",
        "apply": "import",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ImportJob.objects.none()
        user = self.request.user
        qs = ImportJob.objects.select_related("institution", "campus")
        if user.is_superuser:
            return qs
        qs = qs.filter(institution_id=user.institution_id)
        if user.campus_id:
            qs = qs.filter(campus_id=user.campus_id)
        return qs

    def handle_exception(self, exc):
        if isinstance(exc, services.ImportErrorValue):
            return super().handle_exception(ConflictError(detail=str(exc)))
        return super().handle_exception(exc)

    @action(detail=False, methods=["get"])
    def template(self, request):
        return Response({"headers": services.TEMPLATE_HEADERS, "csv": services.template_csv()})

    @action(detail=False, methods=["post"])
    def create_job(self, request):
        institution = getattr(request.user, "institution", None)
        campus = getattr(request.user, "campus", None)
        if not institution:
            raise ValidationError({"institution": "Institution context is required."})
        if not user_can_access_institution(request.user, institution.id):
            raise ValidationError({"institution": "Institution is outside your scope."})
        if campus and not user_can_access_campus_id(request.user, campus.id):
            raise ValidationError({"campus": "Campus is outside your scope."})
        job = services.create_job(
            request.user,
            institution=institution,
            campus=campus,
            dataset=ImportJob.Dataset.STUDENTS,
            source_name=request.data.get("source_name", "manual-upload"),
            dry_run=request.data.get("dry_run", True),
        )
        return Response(ImportJobSerializer(job).data, status=201)

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        payload = PreviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        job = services.preview_job(
            request.user,
            self.get_object(),
            payload.validated_data["payload"],
        )
        return Response(ImportJobSerializer(job).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        job = services.approve_job(request.user, self.get_object())
        return Response(ImportJobSerializer(job).data)

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        job = services.apply_job(request.user, self.get_object())
        return Response(ImportJobSerializer(job).data)

    @action(detail=True, methods=["get"])
    def rows(self, request, pk=None):
        job = self.get_object()
        return Response(
            [
                {
                    "row_number": error.row_number,
                    "field": error.field,
                    "message": error.message,
                    "raw_data": error.raw_data,
                }
                for error in job.row_errors.all()
            ]
        )
