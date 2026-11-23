from django.contrib import admin

from .models import TeacherAssignment, Timetable, TimetableSlot

for model in (TeacherAssignment, Timetable, TimetableSlot):
    admin.site.register(model)
