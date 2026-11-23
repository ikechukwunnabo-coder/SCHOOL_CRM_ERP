from rest_framework import serializers, viewsets
from rest_framework.decorators import action
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
from apps.students.models import Student

from . import services
from .models import AttendanceCorrection, AttendanceRecord, AttendanceSession

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

    def handle_exception(self, exc):
        if isinstance(exc, services.AttendanceError):
            return super().handle_exception(ConflictError(detail=str(exc)))
        return super().handle_exception(exc)


class AttendanceSessionViewSet(ScopedViewSet):
    serializer_class = serializer_for(AttendanceSession)
    queryset = AttendanceSession.objects.all()

    @action(detail=False, methods=["post"], url_path="open")
    def open(self, request):
        session = services.open_session(
            request.user,
            offering=SubjectOffering.objects.get(pk=request.data["offering"]),
            attendance_date=request.data["attendance_date"],
        )
        return Response(self.get_serializer(session).data, status=201)

    @action(detail=True, methods=["post"], url_path="mark")
    def mark(self, request, pk=None):
        record = services.mark_attendance(
            request.user,
            attendance=self.get_object(),
            student=Student.objects.get(pk=request.data["student"]),
            status=request.data["status"],
        )
        return Response(serializer_for(AttendanceRecord)(record).data)

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
