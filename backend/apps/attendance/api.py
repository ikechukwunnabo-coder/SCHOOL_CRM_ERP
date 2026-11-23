from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from apps.academics.models import SubjectOffering
from apps.core.exceptions import ConflictError
from apps.permissions.permissions import (
    HasActiveInstitutionRole,
    HasInstitutionContext,
    HasModuleVerbPermission,
    IsAuthenticatedAndActive,
    IsCampusScoped,
    IsInstitutionScoped,
)
from apps.permissions.services import user_can_access_campus_id, user_can_access_institution
from apps.students.models import Student

from . import services
from .models import (
    AttendanceCorrection,
    AttendanceRecord,
    AttendanceSession,
    TeacherAttendanceRecord,
)

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
    module = "attendance"
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
            raise services.AttendanceError("invalid_date")
        return parsed

    def handle_exception(self, exc):
        if isinstance(exc, services.AttendanceError):
            return super().handle_exception(ConflictError(detail=str(exc)))
        return super().handle_exception(exc)


class AttendanceSessionViewSet(ScopedViewSet):
    serializer_class = serializer_for(AttendanceSession)
    queryset = AttendanceSession.objects.all()
    verb_map = {
        **ScopedViewSet.verb_map,
        "open": "create",
        "mark": "create",
        "close": "update",
        "expected_students": "view",
    }

    @action(detail=False, methods=["post"], url_path="open")
    def open(self, request):
        offering = self.scoped_get(
            SubjectOffering,
            request.data["offering"],
            institution_field="session__institution_id",
            campus_field="session__campus_id",
        )
        session = services.open_session(
            request.user,
            offering=offering,
            attendance_date=self._date(request.data["attendance_date"]),
        )
        return Response(self.get_serializer(session).data, status=201)

    @action(detail=True, methods=["post"], url_path="mark")
    def mark(self, request, pk=None):
        student = self.scoped_get(Student, request.data["student"])
        record = services.mark_attendance(
            request.user,
            attendance=self.get_object(),
            student=student,
            status=request.data["status"],
        )
        return Response(serializer_for(AttendanceRecord)(record).data, status=201)

    @action(detail=True, methods=["get"], url_path="expected-students")
    def expected_students(self, request, pk=None):
        students = services.expected_students(self.get_object())
        return Response(
            [
                {
                    "id": str(student.id),
                    "admission_number": student.admission_number,
                    "name": str(student),
                }
                for student in students
            ]
        )

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        session = services.close_session(request.user, self.get_object())
        return Response(self.get_serializer(session).data)


class AttendanceRecordViewSet(ScopedViewSet):
    serializer_class = serializer_for(AttendanceRecord)
    queryset = AttendanceRecord.objects.all()
    institution_field = "attendance_session__institution_id"
    campus_field = "attendance_session__campus_id"
    verb_map = {**ScopedViewSet.verb_map, "correct": "update"}

    @action(detail=True, methods=["post"], url_path="correct")
    def correct(self, request, pk=None):
        correction = services.correct_attendance(
            request.user,
            record=self.get_object(),
            new_status=request.data["new_status"],
            reason=request.data.get("reason", ""),
        )
        return Response(serializer_for(AttendanceCorrection)(correction).data, status=201)


class AttendanceCorrectionViewSet(ScopedViewSet):
    serializer_class = serializer_for(AttendanceCorrection)
    queryset = AttendanceCorrection.objects.all()
    institution_field = "record__attendance_session__institution_id"
    campus_field = "record__attendance_session__campus_id"


class TeacherAttendanceViewSet(ScopedViewSet):
    serializer_class = serializer_for(TeacherAttendanceRecord)
    queryset = TeacherAttendanceRecord.objects.all()
    filterset_fields = ["employee", "attendance_date", "status", "approval_status"]
    verb_map = {
        **ScopedViewSet.verb_map,
        "mark": "create",
        "approve": "approve",
        "query": "view",
    }

    @action(detail=False, methods=["post"])
    def mark(self, request):
        employee = services.scoped_employee(request.user, request.data["employee"])
        if employee is None:
            raise NotFound("Employee not found in scope.")
        record = services.mark_teacher_attendance(
            request.user,
            employee=employee,
            attendance_date=self._date(request.data["attendance_date"]),
            status=request.data["status"],
        )
        return Response(self.get_serializer(record).data, status=201)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        record = services.approve_teacher_attendance(request.user, self.get_object())
        return Response(self.get_serializer(record).data)

    @action(detail=False, methods=["get"])
    def query(self, request):
        employee = None
        if request.query_params.get("employee"):
            employee = services.scoped_employee(
                request.user, request.query_params["employee"]
            )
            if employee is None:
                raise NotFound("Employee not found in scope.")
        date_from = None
        if request.query_params.get("date_from"):
            date_from = self._date(request.query_params["date_from"])
        date_to = None
        if request.query_params.get("date_to"):
            date_to = self._date(request.query_params["date_to"])
        records = services.query_teacher_attendance(
            request.user,
            employee=employee,
            date_from=date_from,
            date_to=date_to,
            status=request.query_params.get("status"),
        )
        return Response(self.get_serializer(records, many=True).data)

    def perform_update(self, serializer):
        services.ensure_teacher_attendance_editable(serializer.instance)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        services.ensure_teacher_attendance_editable(instance)
        super().perform_destroy(instance)
