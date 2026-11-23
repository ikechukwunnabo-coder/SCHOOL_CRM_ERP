from django.http import FileResponse
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from apps.academics.models import AcademicSession, SubjectOffering, Term
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
from .models import (
    AssessmentComponent,
    AssessmentScheme,
    GradingPolicy,
    GradingScale,
    ReportCard,
    ResultRecord,
)
from .services import ExaminationError

BASE = [
    IsAuthenticatedAndActive,
    HasInstitutionContext,
    HasActiveInstitutionRole,
    HasModuleVerbPermission,
    IsInstitutionScoped,
    IsCampusScoped,
]


def serializer_for(model):
    class Serializer(serializers.ModelSerializer):
        class Meta:
            fields = "__all__"
            read_only_fields = ["id", "created_at", "updated_at"]

    Serializer.Meta.model = model
    return Serializer


class ScopedViewSet(viewsets.ModelViewSet):
    institution_field = "institution_id"
    campus_field = "campus_id"
    module = "examinations"
    verb = "view"
    verb_map = {
        "create": "create",
        "update": "update",
        "partial_update": "update",
        "destroy": "delete_or_archive",
    }
    permission_classes = BASE
    http_method_names = ["get", "post", "head", "options"]

    def initial(self, request, *args, **kwargs):
        if request.method in ("PUT", "PATCH", "DELETE") and self.action in {
            "update",
            "partial_update",
            "destroy",
        }:
            raise MethodNotAllowed(request.method)
        super().initial(request, *args, **kwargs)

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
        if isinstance(exc, ExaminationError):
            return super().handle_exception(ConflictError(detail=str(exc)))
        return super().handle_exception(exc)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)


def _scoped_object(user, model, pk):
    obj = get_object_or_404(model, pk=pk)
    try:
        services.ensure_institution_scope(user, obj)
    except ExaminationError as exc:
        raise PermissionDenied(str(exc)) from exc
    return obj


def _required(data, *keys):
    missing = [key for key in keys if not data.get(key)]
    if missing:
        raise ValidationError({"detail": f"Missing required fields: {', '.join(missing)}"})


class AssessmentSchemeViewSet(ScopedViewSet):
    queryset = AssessmentScheme.objects.select_related("session", "term", "class_level", "arm")
    serializer_class = serializer_for(AssessmentScheme)


class AssessmentComponentViewSet(ScopedViewSet):
    queryset = AssessmentComponent.objects.select_related("scheme")
    serializer_class = serializer_for(AssessmentComponent)
    institution_field = "scheme__institution_id"
    campus_field = "scheme__campus_id"


class GradingScaleViewSet(ScopedViewSet):
    queryset = GradingScale.objects.all()
    serializer_class = serializer_for(GradingScale)


class GradingPolicyViewSet(ScopedViewSet):
    queryset = GradingPolicy.objects.select_related("grading_scale", "institution", "campus")
    serializer_class = serializer_for(GradingPolicy)


class ResultViewSet(ScopedViewSet):
    queryset = ResultRecord.objects.select_related(
        "student", "offering__subject", "scheme", "grading_scale", "session", "term"
    )
    serializer_class = serializer_for(ResultRecord)
    verb_map = {
        **ScopedViewSet.verb_map,
        "submit_results": "submit",
        "return_for_correction": "review",
        "approve": "approve",
        "publish": "publish",
        "correct": "approve",
    }

    def create(self, request, *args, **kwargs):
        _required(request.data, "scheme", "offering", "student", "component_scores")
        scheme = _scoped_object(request.user, AssessmentScheme, request.data["scheme"])
        offering = _scoped_object(request.user, SubjectOffering, request.data["offering"])
        student = _scoped_object(request.user, Student, request.data["student"])
        result = services.record_result(
            request.user,
            scheme=scheme,
            offering=offering,
            student=student,
            component_scores=request.data["component_scores"],
        )
        return Response(self.get_serializer(result).data, status=201)

    @action(detail=False, methods=["post"], url_path="submit")
    def submit_results(self, request):
        _required(request.data, "scheme", "offering")
        scheme = _scoped_object(request.user, AssessmentScheme, request.data["scheme"])
        offering = _scoped_object(request.user, SubjectOffering, request.data["offering"])
        submitted = services.submit_results(request.user, scheme=scheme, offering=offering)
        return Response({"submitted": submitted})

    @action(detail=True, methods=["post"], url_path="return-for-correction")
    def return_for_correction(self, request, pk=None):
        result = self.get_object()
        _required(request.data, "reason")
        updated = services.return_for_correction(
            request.user, result=result, reason=request.data["reason"]
        )
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        result = self.get_object()
        updated = services.approve_result(request.user, result=result)
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        result = self.get_object()
        updated = services.publish_result(request.user, result=result)
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def correct(self, request, pk=None):
        result = self.get_object()
        _required(request.data, "component_scores", "reason")
        updated = services.correct_result(
            request.user,
            result=result,
            component_scores=request.data["component_scores"],
            reason=request.data["reason"],
        )
        return Response(self.get_serializer(updated).data)


class ReportCardViewSet(ScopedViewSet):
    queryset = ReportCard.objects.select_related("student", "session", "term")
    serializer_class = serializer_for(ReportCard)
    verb_map = {
        **ScopedViewSet.verb_map,
        "generate": "create",
        "download": "print",
    }

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        _required(request.data, "student", "session")
        student = _scoped_object(request.user, Student, request.data["student"])
        session = _scoped_object(request.user, AcademicSession, request.data["session"])
        term = None
        if request.data.get("term"):
            term = _scoped_object(request.user, Term, request.data["term"])
        card = services.generate_report_card(
            request.user,
            student=student,
            session=session,
            term=term,
        )
        return Response(self.get_serializer(card).data)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        card = self.get_object()
        file_handle = services.prepare_report_card_download(request.user, report_card=card)
        return FileResponse(
            file_handle.open("rb"),
            as_attachment=True,
            filename=f"{card.reference}-v{card.version}.pdf",
            content_type="application/pdf",
        )
