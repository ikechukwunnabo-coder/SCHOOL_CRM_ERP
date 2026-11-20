from django.contrib import admin

from .models import Campus, Institution


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    search_fields = ("name", "code")
    list_filter = ("is_active",)


@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "institution", "is_active", "created_at")
    search_fields = ("name", "code", "institution__name")
    list_filter = ("is_active", "institution")
