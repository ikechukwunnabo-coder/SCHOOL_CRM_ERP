from rest_framework import serializers, viewsets

from apps.permissions.permissions import (
    HasActiveInstitutionRole,
    HasInstitutionContext,
    IsAuthenticatedAndActive,
    IsCampusScoped,
    IsInstitutionScoped,
)

from .models import Campus, Institution


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = ["id", "name", "code", "is_active"]
        read_only_fields = fields


class CampusSerializer(serializers.ModelSerializer):
    institution_code = serializers.CharField(source="institution.code", read_only=True)

    class Meta:
        model = Campus
        fields = [
            "id",
            "institution",
            "institution_code",
            "name",
            "code",
            "address",
            "is_active",
        ]
        read_only_fields = fields


class ScopedReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [
        IsAuthenticatedAndActive,
        HasInstitutionContext,
        HasActiveInstitutionRole,
        IsInstitutionScoped,
    ]


class InstitutionViewSet(ScopedReadOnlyViewSet):
    serializer_class = InstitutionSerializer
    queryset = Institution.objects.all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Institution.objects.none()
        user = self.request.user
        if user.is_superuser:
            return Institution.objects.all()
        return Institution.objects.filter(pk=user.institution_id)


class CampusViewSet(ScopedReadOnlyViewSet):
    serializer_class = CampusSerializer
    queryset = Campus.objects.all()
    permission_classes = ScopedReadOnlyViewSet.permission_classes + [IsCampusScoped]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Campus.objects.none()
        user = self.request.user
        if user.is_superuser:
            return Campus.objects.select_related("institution")
        qs = Campus.objects.filter(institution_id=user.institution_id).select_related(
            "institution"
        )
        if user.campus_id:
            qs = qs.filter(pk=user.campus_id)
        return qs
