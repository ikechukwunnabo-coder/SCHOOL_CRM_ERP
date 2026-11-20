from django.contrib import admin

from .models import ImportJob, ImportRowError

admin.site.register(ImportJob)
admin.site.register(ImportRowError)
