from rest_framework import serializers, viewsets

from apps.permissions.permissions import (
    HasActiveInstitutionRole,
    HasInstitutionContext,
    HasModuleVerbPermission,
    IsAuthenticatedAndActive,
    IsCampusScoped,
    IsInstitutionScoped,
)

from .models import Employee


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.all()
    module = "employees"
    verb = "view"
    verb_map = {
        "create": "create",
        "update": "update",
        "partial_update": "update",
        "destroy": "delete_or_archive",
    }
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
            return Employee.objects.none()
        user = self.request.user
        qs = Employee.objects.select_related("institution", "campus")
        if user.is_superuser:
            return qs
        qs = qs.filter(institution_id=user.institution_id)
        if user.campus_id:
            qs = qs.filter(campus_id=user.campus_id)
        return qs
