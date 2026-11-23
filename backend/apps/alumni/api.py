from rest_framework import serializers, viewsets

from apps.permissions.permissions import (
    HasActiveInstitutionRole,
    HasInstitutionContext,
    HasModuleVerbPermission,
    IsAuthenticatedAndActive,
    IsCampusScoped,
    IsInstitutionScoped,
)

from .models import AlumniRecord


class AlumniRecordSerializer(serializers.ModelSerializer):
    student_admission_number = serializers.CharField(
        source="student.admission_number", read_only=True
    )

    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = AlumniRecord
        fields = [
            "id",
            "institution",
            "campus",
            "student",
            "student_admission_number",
            "student_name",
            "graduation_event",
            "graduation_date",
            "graduation_reference",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AlumniRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AlumniRecord.objects.select_related("institution", "campus", "student")
    serializer_class = AlumniRecordSerializer
    module = "alumni"
    verb = "view"
    permission_classes = [
        IsAuthenticatedAndActive,
        HasInstitutionContext,
        HasActiveInstitutionRole,
        HasModuleVerbPermission,
        IsInstitutionScoped,
        IsCampusScoped,
    ]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        qs = self.queryset
        if user.is_superuser:
            return qs
        qs = qs.filter(institution_id=user.institution_id)
        if user.campus_id:
            qs = qs.filter(campus_id=user.campus_id)
        return qs
