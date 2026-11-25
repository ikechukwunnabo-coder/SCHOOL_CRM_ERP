from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
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
from apps.permissions.services import (
    get_user_role_names,
    user_can_access_campus_id,
    user_can_access_institution,
)

from . import services
from .models import TeacherAssignment, TeacherWorkloadPolicy, Timetable, TimetableSlot

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

    def _ensure_scope(self, obj):
        user = self.request.user
        if user.is_superuser:
            return
        institution_id = getattr(obj, "institution_id", None)
        campus_id = getattr(obj, "campus_id", None)
        if not user_can_access_institution(user, institution_id):
            raise PermissionDenied("Outside institution scope.")
        if not user_can_access_campus_id(user, campus_id):
            raise PermissionDenied("Outside campus scope.")

    def _candidate(self, serializer):
        if serializer.instance is None:
            return self.queryset.model(**serializer.validated_data)
        for field, value in serializer.validated_data.items():
            setattr(serializer.instance, field, value)
        return serializer.instance

    def perform_create(self, serializer):
        self._ensure_scope(self._candidate(serializer))
        serializer.save()

    def perform_update(self, serializer):
        self._ensure_scope(self._candidate(serializer))
        serializer.save()

    def scoped_get(
        self,
        model,
        pk,
        *,
        institution_field="institution_id",
        campus_field="campus_id",
    ):
        qs = model.objects.all()
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(**{institution_field: user.institution_id})
            if user.campus_id and campus_field:
                qs = qs.filter(**{campus_field: user.campus_id})
        return get_object_or_404(qs, pk=pk)

    def _date(self, value):
        parsed = parse_date(value) if isinstance(value, str) else value
        if parsed is None:
            raise services.TeachingError("invalid_date")
        return parsed

    def handle_exception(self, exc):
        if isinstance(exc, services.TeachingError):
            return super().handle_exception(ConflictError(detail=str(exc)))
        return super().handle_exception(exc)


class WorkloadPolicyViewSet(ScopedViewSet):
    serializer_class = serializer_for(TeacherWorkloadPolicy)
    queryset = TeacherWorkloadPolicy.objects.all()
    filterset_fields = ["institution", "campus", "effective_from"]


class TeacherPortalViewSet(viewsets.ViewSet):
    permission_classes = BASE
    module = "teaching"
    verb = "view"

    def list(self, request):
        from apps.permissions.roles import TEACHING_ROLES, HOD, PRINCIPAL, VICE_PRINCIPAL

        allowed = set(TEACHING_ROLES) | {HOD, PRINCIPAL, VICE_PRINCIPAL}
        if not request.user.is_superuser and not (set(get_user_role_names(request.user)) & allowed):
            raise PermissionDenied("You do not have permission for teaching.view.")
        today = timezone.localdate()
        assignments = services.resolve_teacher_scope(request.user)
        from apps.attendance.models import AttendanceSession, TeacherAttendanceRecord

        employee_ids = {a.employee_id for a in assignments}
        offering_ids = {a.offering_id for a in assignments}
        timetable_ids = list(
            Timetable.objects.filter(
                session__institution_id=request.user.institution_id, status="published"
            ).values_list("id", flat=True)
        )
        slots = TimetableSlot.objects.filter(
            timetable_id__in=timetable_ids, offering_id__in=offering_ids
        ).select_related("offering", "employee", "timetable")[:100]
        attendance_sessions = AttendanceSession.objects.filter(
            offering_id__in=offering_ids, attendance_date__gte=today - timedelta(days=14)
        ).order_by("-attendance_date")[:50]
        teacher_attendance = TeacherAttendanceRecord.objects.filter(
            employee_id__in=employee_ids
        ).order_by("-attendance_date")[:30]
        return Response(
            {
                "teacher": {
                    "employee_ids": list(employee_ids),
                    "assignment_count": len(assignments),
                },
                "assignments": serializer_for(TeacherAssignment)(assignments, many=True).data,
                "timetable_slots": serializer_for(TimetableSlot)(slots, many=True).data,
                "attendance_sessions": [
                    {
                        "id": s.id,
                        "offering_id": s.offering_id,
                        "attendance_date": s.attendance_date,
                        "status": s.status,
                    }
                    for s in attendance_sessions
                ],
                "teacher_attendance": serializer_for(TeacherAttendanceRecord)(
                    teacher_attendance, many=True
                ).data,
            }
        )


class AssignmentViewSet(ScopedViewSet):
    serializer_class = serializer_for(TeacherAssignment)
    queryset = TeacherAssignment.objects.all()
    verb_map = {**ScopedViewSet.verb_map, "reassign": "update"}

    @action(detail=False, methods=["get"], url_path="my-assignments")
    def my_assignments(self, request):
        visible = {item.pk for item in self.get_queryset()}
        assignments = [
            item
            for item in services.resolve_teacher_scope(request.user)
            if item.pk in visible
        ]
        return Response(self.get_serializer(assignments, many=True).data)

    @action(detail=True, methods=["post"])
    def reassign(self, request, pk=None):
        assignment = self.get_object()
        try:
            workload = int(request.data.get("workload_hours", assignment.workload_hours))
        except (TypeError, ValueError) as exc:
            raise services.TeachingError("invalid_workload_hours") from exc
        updated = services.assign_teacher(
            request.user,
            offering=assignment.offering,
            employee=assignment.employee,
            role=assignment.role,
            start_date=self._date(request.data["start_date"]),
            end_date=self._date(request.data["end_date"]),
            workload_hours=workload,
            reassign=True,
        )
        return Response(self.get_serializer(updated).data)


class TimetableViewSet(ScopedViewSet):
    serializer_class = serializer_for(Timetable)
    queryset = Timetable.objects.all()
    institution_field = "session__institution_id"
    campus_field = "session__campus_id"
    verb_map = {
        **ScopedViewSet.verb_map,
        "add_slot": "create",
        "approve": "approve",
        "publish": "publish",
        "revise": "create",
    }

    @action(detail=True, methods=["post"], url_path="add-slot")
    def add_slot(self, request, pk=None):
        from apps.academics.models import SubjectOffering
        from apps.employees.models import Employee

        offering = self.scoped_get(
            SubjectOffering,
            request.data["offering"],
            institution_field="session__institution_id",
            campus_field="session__campus_id",
        )
        employee = self.scoped_get(Employee, request.data["employee"])
        recurrence_until = request.data.get("recurrence_until")
        slot = services.add_slot(
            request.user,
            timetable=self.get_object(),
            day_of_week=int(request.data["day_of_week"]),
            period=int(request.data["period"]),
            offering=offering,
            employee=employee,
            room=request.data.get("room", ""),
            recurrence=request.data.get("recurrence", TimetableSlot.Recurrence.WEEKLY),
            recurrence_interval=int(request.data.get("recurrence_interval", 1)),
            recurrence_until=self._date(recurrence_until) if recurrence_until else None,
        )
        return Response(serializer_for(TimetableSlot)(slot).data, status=201)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        timetable = services.approve_timetable(request.user, self.get_object())
        return Response(self.get_serializer(timetable).data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        timetable = services.publish_timetable(request.user, self.get_object())
        return Response(self.get_serializer(timetable).data)

    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        revision = services.create_timetable_revision(request.user, self.get_object())
        return Response(self.get_serializer(revision).data, status=201)

    def perform_update(self, serializer):
        services.ensure_timetable_editable(serializer.instance)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        services.ensure_timetable_editable(instance)
        super().perform_destroy(instance)


class TimetableSlotViewSet(ScopedViewSet):
    serializer_class = serializer_for(TimetableSlot)
    queryset = TimetableSlot.objects.all()
    institution_field = "timetable__session__institution_id"
    campus_field = "timetable__session__campus_id"

    def perform_create(self, serializer):
        services.ensure_slot_editable(
            TimetableSlot(timetable=serializer.validated_data["timetable"])
        )
        services.validate_recurrence(
            recurrence=serializer.validated_data.get(
                "recurrence", TimetableSlot.Recurrence.WEEKLY
            ),
            interval=serializer.validated_data.get("recurrence_interval", 1),
            until=serializer.validated_data.get("recurrence_until"),
        )
        super().perform_create(serializer)

    def perform_update(self, serializer):
        services.ensure_slot_editable(serializer.instance)
        services.validate_recurrence(
            recurrence=serializer.validated_data.get(
                "recurrence", serializer.instance.recurrence
            ),
            interval=serializer.validated_data.get(
                "recurrence_interval", serializer.instance.recurrence_interval
            ),
            until=serializer.validated_data.get(
                "recurrence_until", serializer.instance.recurrence_until
            ),
        )
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        services.ensure_slot_editable(instance)
        super().perform_destroy(instance)
