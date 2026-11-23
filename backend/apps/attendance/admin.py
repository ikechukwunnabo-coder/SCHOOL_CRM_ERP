from django.contrib import admin

from .models import AttendanceCorrection, AttendanceRecord, AttendanceSession

for model in (AttendanceSession, AttendanceRecord, AttendanceCorrection):
    admin.site.register(model)
