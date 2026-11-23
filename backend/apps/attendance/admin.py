from django.contrib import admin

from .models import (
    AttendanceCorrection,
    AttendanceRecord,
    AttendanceSession,
    TeacherAttendanceRecord,
)

for model in (
    AttendanceSession,
    AttendanceRecord,
    AttendanceCorrection,
    TeacherAttendanceRecord,
):
    admin.site.register(model)
