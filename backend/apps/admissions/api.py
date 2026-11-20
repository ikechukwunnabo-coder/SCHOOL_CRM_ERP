from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.admissions.permissions import (
    ADMISSION_DECIDE_ROLES,
    ADMISSION_MANAGE_ROLES,
    ADMISSION_VIEW_ROLES,
)
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
from apps.permissions.services import user_can_access_campus_id, user_can_access_institution
from apps.students.services import StudentWorkflowError

from . import services
from .models import AdmissionDecision, Application, ApplicationDocument, Enquiry

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


def _resolve_campus(serializer, attrs, institution):
    user = serializer.context["request"].user
    campus = attrs.get("campus") or getattr(serializer.instance, "campus", None)
    if campus is None and not user.is_superuser:
        campus = getattr(user, "campus", None)
    if campus:
        if campus.institution_id != institution.id:
            raise ValidationError({"campus": "Campus belongs to another institution."})
        if not user.is_superuser and not user_can_access_campus_id(user, campus.id):
            raise ValidationError({"campus": "Campus is outside your scope."})
    return campus


class ScopedAdmissionViewSet(viewsets.ModelViewSet):
    permission_classes = BASE_PERMISSIONS
    allowed_roles = ADMISSION_MANAGE_ROLES

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

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def handle_exception(self, exc):
        if isinstance(exc, (services.WorkflowError, StudentWorkflowError)):
            return super().handle_exception(ConflictError(detail=str(exc)))
        return super().handle_exception(exc)


class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = [
            "id",
            "institution",
            "campus",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "email",
            "phone",
            "intended_class",
            "source",
            "status",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]
        extra_kwargs = {"institution": {"required": False}}

    def validate(self, attrs):
        institution = _resolve_institution(self, attrs)
        attrs["institution"] = institution
        attrs["campus"] = _resolve_campus(self, attrs, institution)
        return attrs


class EnquiryViewSet(ScopedAdmissionViewSet):
    serializer_class = EnquirySerializer
    queryset = Enquiry.objects.all()
    allowed_roles = ADMISSION_MANAGE_ROLES

    def perform_create(self, serializer):
        enquiry = services.create_enquiry(self.request.user, **serializer.validated_data)
        serializer.instance = enquiry


class ApplicationSerializer(serializers.ModelSerializer):
    institution_code = serializers.CharField(source="institution.code", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "institution",
            "institution_code",
            "campus",
            "enquiry",
            "application_number",
            "cycle",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "email",
            "phone",
            "intended_class",
            "status",
            "submitted_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "application_number",
            "status",
            "submitted_at",
            "created_at",
            "institution_code",
        ]
        extra_kwargs = {
            "institution": {"required": False},
            "cycle": {"required": False},
        }

    def validate(self, attrs):
        institution = _resolve_institution(self, attrs)
        attrs["campus"] = _resolve_campus(self, attrs, institution)
        enquiry = attrs.get("enquiry") or getattr(self.instance, "enquiry", None)
        if enquiry and enquiry.institution_id != institution.id:
            raise ValidationError({"enquiry": "Enquiry belongs to another institution."})
        attrs["institution"] = institution
        return attrs


class DecisionSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=AdmissionDecision.Outcome.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class GuardianLinkSerializer(serializers.Serializer):
    guardian = serializers.UUIDField()
    relationship = serializers.CharField(max_length=64)
    is_primary = serializers.BooleanField(required=False, default=False)
    financial_responsibility = serializers.BooleanField(required=False, default=False)
    authorized_pickup = serializers.BooleanField(required=False, default=False)
    portal_access = serializers.BooleanField(required=False, default=False)


class EnrolSerializer(serializers.Serializer):
    guardian_links = GuardianLinkSerializer(many=True, required=False, default=list)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ApplicationViewSet(ScopedAdmissionViewSet):
    serializer_class = ApplicationSerializer
    queryset = Application.objects.all()
    allowed_roles = ADMISSION_VIEW_ROLES

    def get_permissions(self):
        if self.action in {"decide", "offer", "accept", "enrol"}:
            self.allowed_roles = ADMISSION_DECIDE_ROLES
        return super().get_permissions()

    def perform_create(self, serializer):
        application = services.create_application(self.request.user, **serializer.validated_data)
        serializer.instance = application

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        application = services.submit_application(request.user, self.get_object())
        return Response(ApplicationSerializer(application).data)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        application = services.review_application(request.user, self.get_object())
        return Response(ApplicationSerializer(application).data)

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        payload = DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        decision = services.record_decision(
            request.user,
            self.get_object(),
            payload.validated_data["outcome"],
            notes=payload.validated_data["notes"],
        )
        return Response(
            {
                "application": ApplicationSerializer(decision.application).data,
                "decision_id": str(decision.pk),
            }
        )

    @action(detail=True, methods=["post"])
    def offer(self, request, pk=None):
        application = services.offer_application(request.user, self.get_object())
        return Response(ApplicationSerializer(application).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        application = services.accept_application(request.user, self.get_object())
        return Response(ApplicationSerializer(application).data)

    @action(detail=True, methods=["post"])
    def enrol(self, request, pk=None):
        application = self.get_object()
        payload = EnrolSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        link_data = payload.validated_data["guardian_links"]
        ids = [str(item["guardian"]) for item in link_data]
        guardian_qs = Guardian.objects.filter(
            pk__in=ids,
            institution_id=application.institution_id,
        )
        guardians = {str(item.pk): item for item in guardian_qs}
        if len(guardians) != len(set(ids)):
            raise ValidationError({"guardian_links": "Unknown or cross-institution guardian."})
        links = [
            {**item, "guardian": guardians[str(item["guardian"])]}
            for item in link_data
        ]
        student = services.enrol_application(
            request.user,
            application,
            guardian_links=links,
            reason=payload.validated_data["reason"],
        )
        return Response(
            {
                "application": ApplicationSerializer(application).data,
                "student_id": str(student.pk),
                "admission_number": student.admission_number,
            }
        )


class ApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationDocument
        fields = [
            "id",
            "application",
            "checklist_item",
            "original_name",
            "file_ref",
            "content_type",
            "size_bytes",
            "review_status",
            "reviewed_at",
        ]
        read_only_fields = fields


class ApplicationDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ApplicationDocumentSerializer
    permission_classes = BASE_PERMISSIONS
    allowed_roles = ADMISSION_VIEW_ROLES

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ApplicationDocument.objects.none()
        user = self.request.user
        qs = ApplicationDocument.objects.select_related("application")
        if user.is_superuser:
            return qs
        qs = qs.filter(application__institution_id=user.institution_id)
        if user.campus_id:
            qs = qs.filter(application__campus_id=user.campus_id)
        return qs
