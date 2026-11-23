from rest_framework import serializers, viewsets
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

from . import services
from .models import AcademicSession, Arm, ClassEnrolment, ClassLevel, Subject, SubjectOffering, Term

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
    module = "academics"
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
        if isinstance(exc, services.AcademicWorkflowError):
            return super().handle_exception(ConflictError(detail=str(exc)))
        return super().handle_exception(exc)


class SessionViewSet(ScopedViewSet):
    serializer_class = serializer_for(AcademicSession)
    queryset = AcademicSession.objects.all()

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        session = services.close_session(request.user, self.get_object())
        return Response(self.get_serializer(session).data)


class TermViewSet(ScopedViewSet):
    serializer_class = serializer_for(Term)
    queryset = Term.objects.all()
    institution_field = "session__institution_id"
    campus_field = "session__campus_id"


class ClassLevelViewSet(ScopedViewSet):
    serializer_class = serializer_for(ClassLevel)
    queryset = ClassLevel.objects.all()


class ArmViewSet(ScopedViewSet):
    serializer_class = serializer_for(Arm)
    queryset = Arm.objects.all()
    institution_field = "class_level__institution_id"
    campus_field = "class_level__campus_id"


class SubjectViewSet(ScopedViewSet):
    serializer_class = serializer_for(Subject)
    queryset = Subject.objects.all()


class SubjectOfferingViewSet(ScopedViewSet):
    serializer_class = serializer_for(SubjectOffering)
    queryset = SubjectOffering.objects.all()
    institution_field = "session__institution_id"
    campus_field = "session__campus_id"


class ClassEnrolmentViewSet(ScopedViewSet):
    serializer_class = serializer_for(ClassEnrolment)
    queryset = ClassEnrolment.objects.all()
    institution_field = "session__institution_id"
    campus_field = "session__campus_id"
