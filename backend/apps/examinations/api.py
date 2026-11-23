from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
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
    }

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
