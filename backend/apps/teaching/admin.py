from django.contrib import admin

from .models import TeacherAssignment, TeacherWorkloadPolicy, Timetable, TimetableSlot

for model in (TeacherWorkloadPolicy, TeacherAssignment, Timetable, TimetableSlot):
    admin.site.register(model)
