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
from .models import TeacherAssignment, Timetable, TimetableSlot

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
    module = "teaching"
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
        if isinstance(exc, services.TeachingError):
            return super().handle_exception(ConflictError(detail=str(exc)))
        return super().handle_exception(exc)


class AssignmentViewSet(ScopedViewSet):
    serializer_class = serializer_for(TeacherAssignment)
    queryset = TeacherAssignment.objects.all()

    @action(detail=False, methods=["get"], url_path="my-assignments")
    def my_assignments(self, request):
        data = self.get_serializer(services.resolve_teacher_scope(request.user), many=True).data
        return Response(data)

    @action(detail=True, methods=["post"])
    def reassign(self, request, pk=None):
        assignment = self.get_object()
        updated = services.assign_teacher(
            request.user,
            offering=assignment.offering,
            employee=assignment.employee,
            role=assignment.role,
            start_date=request.data["start_date"],
            end_date=request.data["end_date"],
            workload_hours=int(request.data.get("workload_hours", assignment.workload_hours)),
            reassign=True,
        )
        return Response(self.get_serializer(updated).data)


class TimetableViewSet(ScopedViewSet):
    serializer_class = serializer_for(Timetable)
    queryset = Timetable.objects.all()
    institution_field = "session__institution_id"
    campus_field = "session__campus_id"

    @action(detail=True, methods=["post"], url_path="add-slot")
    def add_slot(self, request, pk=None):
        from apps.academics.models import SubjectOffering
        from apps.employees.models import Employee

        slot = services.add_slot(
            request.user,
            timetable=self.get_object(),
            day_of_week=int(request.data["day_of_week"]),
            period=int(request.data["period"]),
            offering=SubjectOffering.objects.get(pk=request.data["offering"]),
            employee=Employee.objects.get(pk=request.data["employee"]),
            room=request.data.get("room", ""),
        )
        return Response(serializer_for(TimetableSlot)(slot).data)


class TimetableSlotViewSet(ScopedViewSet):
    serializer_class = serializer_for(TimetableSlot)
    queryset = TimetableSlot.objects.all()
    institution_field = "timetable__session__institution_id"
    campus_field = "timetable__session__campus_id"
