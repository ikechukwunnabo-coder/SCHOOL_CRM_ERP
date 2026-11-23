from django.http import FileResponse
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
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
from apps.students.models import Student

from . import services
from .models import Transcript, TranscriptEvent, TranscriptRequest, TranscriptVerification
from .services import TranscriptError

BASE = [
    IsAuthenticatedAndActive,
    HasInstitutionContext,
    HasActiveInstitutionRole,
    HasModuleVerbPermission,
    IsInstitutionScoped,
    IsCampusScoped,
]


class TranscriptRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptRequest
        fields = "__all__"
        read_only_fields = [
            "institution",
            "campus",
            "student",
            "requested_by",
            "status",
            "decision_reason",
            "reviewed_by",
            "approved_by",
            "reviewed_at",
            "approved_at",
            "created_at",
            "updated_at",
        ]


class TranscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcript
        fields = [
            "id",
            "institution",
            "campus",
            "student",
            "request",
            "supersedes",
            "reference_number",
            "version",
            "kind",
            "status",
            "template_version",
            "issued_to",
            "issue_purpose",
            "issued_by",
            "approved_by",
            "issued_at",
            "completeness",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TranscriptEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptEvent
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class TranscriptVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptVerification
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class VerifyTranscriptSerializer(serializers.Serializer):
    token = serializers.CharField(trim_whitespace=True)


class ScopedViewSet(viewsets.ModelViewSet):
    institution_field = "institution_id"
    campus_field = "campus_id"
    module = "transcripts"
    verb = "view"
    verb_map = {
        "create": "create",
        "update": "update",
        "partial_update": "update",
        "destroy": "delete_or_archive",
    }
    permission_classes = BASE

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        qs = self.queryset
        if user.is_superuser:
            return qs
        qs = qs.filter(**{self.institution_field: user.institution_id})
        if user.campus_id and self.campus_field:
            qs = qs.filter(**{self.campus_field: user.campus_id})
        return qs

    def handle_exception(self, exc):
        if isinstance(exc, TranscriptError):
            return super().handle_exception(ConflictError(detail=str(exc)))
        return super().handle_exception(exc)


def _scoped_object(user, model, pk):
    obj = get_object_or_404(model, pk=pk)
    try:
        services.ensure_institution_scope(
            user,
            institution_id=obj.institution_id,
            campus_id=getattr(obj, "campus_id", None),
        )
    except TranscriptError as exc:
        raise PermissionDenied(str(exc)) from exc
    return obj


def _required(data, *keys):
    missing = [key for key in keys if not data.get(key)]
    if missing:
        raise ValidationError({"detail": f"Missing required fields: {', '.join(missing)}"})


class TranscriptRequestViewSet(ScopedViewSet):
    queryset = TranscriptRequest.objects.select_related(
        "institution", "campus", "student", "requested_by", "reviewed_by", "approved_by"
    )
    serializer_class = TranscriptRequestSerializer
    http_method_names = ["get", "post", "head", "options"]
    verb_map = {
        **ScopedViewSet.verb_map,
        "review": "review",
        "approve": "approve",
        "reject": "review",
        "generate": "create",
    }

    def create(self, request):
        _required(request.data, "student", "purpose")
        student = _scoped_object(request.user, Student, request.data["student"])
        request_obj = services.request_transcript(
            request.user,
            student=student,
            purpose=request.data["purpose"],
            requested_kind=request.data.get("requested_kind", "official"),
        )
        return Response(self.get_serializer(request_obj).data, status=201)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        request_obj = self.get_object()
        updated = services.review_transcript_request(
            request.user,
            request=request_obj,
            reason=request.data.get("reason", ""),
        )
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        request_obj = self.get_object()
        updated = services.approve_transcript_request(
            request.user,
            request=request_obj,
            reason=request.data.get("reason", ""),
        )
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        request_obj = self.get_object()
        _required(request.data, "reason")
        updated = services.reject_transcript_request(
            request.user,
            request=request_obj,
            reason=request.data["reason"],
        )
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        request_obj = self.get_object()
        transcript, raw_token = services.generate_transcript(request.user, request=request_obj)
        data = TranscriptSerializer(transcript).data
        data["verification_token"] = raw_token
        return Response(data, status=201)


class TranscriptViewSet(ScopedViewSet):
    queryset = Transcript.objects.select_related("institution", "campus", "student", "request")
    serializer_class = TranscriptSerializer
    http_method_names = ["get", "post", "head", "options"]
    verb_map = {
        **ScopedViewSet.verb_map,
        "download": "download",
        "issue": "issue_or_revoke",
        "revoke": "issue_or_revoke",
        "correct": "update",
        "verifications": "view",
    }

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def verify(self, request):
        serializer = VerifyTranscriptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(services.verify_transcript(serializer.validated_data["token"]))

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        transcript = self.get_object()
        _required(request.data, "issued_to")
        updated = services.issue_transcript(
            request.user,
            transcript=transcript,
            issued_to=request.data["issued_to"],
            purpose=request.data.get("purpose", ""),
        )
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def correct(self, request, pk=None):
        transcript = self.get_object()
        _required(request.data, "reason")
        corrected, raw_token = services.correct_transcript(
            request.user,
            transcript=transcript,
            reason=request.data["reason"],
            issued_to=request.data.get("issued_to", ""),
            purpose=request.data.get("purpose", ""),
        )
        data = self.get_serializer(corrected).data
        data["verification_token"] = raw_token
        return Response(data, status=201)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        transcript = self.get_object()
        _required(request.data, "reason")
        updated = services.revoke_transcript(
            request.user,
            transcript=transcript,
            reason=request.data["reason"],
        )
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["get"])
    def verifications(self, request, pk=None):
        transcript = self.get_object()
        serializer = TranscriptVerificationSerializer(
            transcript.verifications.all(),
            many=True,
        )
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        transcript = self.get_object()
        file_handle = services.prepare_transcript_download(request.user, transcript=transcript)
        return FileResponse(
            file_handle.open("rb"),
            as_attachment=True,
            filename=f"{transcript.reference_number}.pdf",
            content_type="application/pdf",
        )
