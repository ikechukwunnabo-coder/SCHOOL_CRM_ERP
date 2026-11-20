from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.audit.services import log_event
from apps.core.exceptions import ConflictError
from apps.guardians.models import Guardian
from apps.permissions.permissions import (
    HasActiveInstitutionRole,
    HasInstitutionContext,
    HasRole,
    IsAuthenticatedAndActive,
    IsCampusScoped,
    IsInstitutionScoped,
)
from apps.permissions.services import user_can_access_institution
from apps.students.permissions import STUDENT_MANAGE_ROLES, STUDENT_VIEW_ROLES

from . import services
from .models import Student, StudentGuardian

BASE_PERMISSIONS = [
    IsAuthenticatedAndActive,
    HasInstitutionContext,
    HasActiveInstitutionRole,
    HasRole,
    IsInstitutionScoped,
    IsCampusScoped,
]


def _resolve_institution(serializer, attrs):
    user = serializer.context["request"].user
    institution = attrs.get("institution") or getattr(serializer.instance, "institution", None)
    if institution is None:
        institution = getattr(user, "institution", None)
    if institution is None:
        raise ValidationError({"institution": "An institution is required."})
    if not user.is_superuser and not user_can_access_institution(user, institution.id):
        raise ValidationError({"institution": "Institution is outside your scope."})
    return institution


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            "id",
            "institution",
            "campus",
            "admission_number",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "status",
            "admission_date",
            "created_at",
        ]
        read_only_fields = fields


class GuardianSerializer(serializers.ModelSerializer):
    institution_code = serializers.CharField(source="institution.code", read_only=True)

    class Meta:
        model = Guardian
        fields = [
            "id",
            "institution",
            "institution_code",
            "first_name",
            "last_name",
            "phone",
            "email",
            "address",
            "preferences",
            "consent",
            "created_at",
        ]
        read_only_fields = ["id", "institution_code", "created_at"]

    def validate(self, attrs):
        attrs["institution"] = _resolve_institution(self, attrs)
        return attrs


class StudentGuardianSerializer(serializers.ModelSerializer):
    guardian_name = serializers.CharField(source="guardian.full_name", read_only=True)

    class Meta:
        model = StudentGuardian
        fields = [
            "id",
            "student",
            "guardian",
            "guardian_name",
            "relationship",
            "is_primary",
            "financial_responsibility",
            "authorized_pickup",
            "portal_access",
            "created_at",
        ]
        read_only_fields = fields


class LifecycleSerializer(serializers.Serializer):
    to_status = serializers.ChoiceField(choices=Student.LifecycleStatus.choices)
    effective_date = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class GuardianLinkSerializer(serializers.Serializer):
    guardian = serializers.UUIDField()
    relationship = serializers.CharField(max_length=64)
    is_primary = serializers.BooleanField(required=False, default=False)
    financial_responsibility = serializers.BooleanField(required=False, default=False)
    authorized_pickup = serializers.BooleanField(required=False, default=False)
    portal_access = serializers.BooleanField(required=False, default=False)


class ScopedStudentViewSet(viewsets.GenericViewSet):
    permission_classes = BASE_PERMISSIONS

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        qs = self.queryset.select_related("institution", "campus")
        if user.is_superuser:
            return qs
        qs = qs.filter(institution_id=user.institution_id)
        if user.campus_id:
            qs = qs.filter(campus_id=user.campus_id)
        return qs

    def handle_exception(self, exc):
        if isinstance(exc, services.StudentWorkflowError):
            return super().handle_exception(ConflictError(detail=str(exc)))
        return super().handle_exception(exc)


class StudentViewSet(ScopedStudentViewSet, viewsets.ReadOnlyModelViewSet):
    serializer_class = StudentSerializer
    queryset = Student.objects.all()
    allowed_roles = STUDENT_VIEW_ROLES

    def get_permissions(self):
        if self.action in {"lifecycle", "guardians"} and self.request.method != "GET":
            self.allowed_roles = STUDENT_MANAGE_ROLES
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def lifecycle(self, request, pk=None):
        student = self.get_object()
        payload = LifecycleSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        updated = services.change_lifecycle(
            request.user,
            student,
            payload.validated_data["to_status"],
            effective_date=payload.validated_data["effective_date"],
            reason=payload.validated_data["reason"],
        )
        return Response(StudentSerializer(updated).data)

    @action(detail=True, methods=["get", "post"])
    def guardians(self, request, pk=None):
        student = self.get_object()
        if request.method == "GET":
            links = StudentGuardian.objects.filter(student=student).select_related("guardian")
            return Response(StudentGuardianSerializer(links, many=True).data)
        payload = GuardianLinkSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        guardian = Guardian.objects.filter(
            pk=payload.validated_data["guardian"],
            institution_id=student.institution_id,
        ).first()
        if guardian is None:
            raise ValidationError({"guardian": "Unknown or cross-institution guardian."})
        fields = dict(payload.validated_data)
        fields.pop("guardian")
        link = services.link_guardian(request.user, student, guardian, **fields)
        return Response(StudentGuardianSerializer(link).data, status=201)


class GuardianViewSet(ScopedStudentViewSet, viewsets.ModelViewSet):
    serializer_class = GuardianSerializer
    queryset = Guardian.objects.all()
    allowed_roles = STUDENT_MANAGE_ROLES

    def perform_create(self, serializer):
        guardian = serializer.save(created_by=self.request.user)
        log_event(
            "guardians.created",
            actor=self.request.user,
            target_type="guardians.Guardian",
            target_id=guardian.pk,
            institution_id=guardian.institution_id,
            change_summary={"full_name": guardian.full_name},
        )
