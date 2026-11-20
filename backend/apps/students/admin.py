from django.contrib import admin

from .models import Student, StudentGuardian, StudentLifecycleEvent

admin.site.register(Student)
admin.site.register(StudentGuardian)
admin.site.register(StudentLifecycleEvent)
