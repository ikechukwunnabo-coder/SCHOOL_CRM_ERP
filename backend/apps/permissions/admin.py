from django.contrib import admin

from .models import Role, UserRole


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "is_system", "created_at")
    list_filter = ("is_system", "institution")
    search_fields = ("name",)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "scope_type", "scope_ref_id", "is_active")
    list_filter = ("scope_type", "is_active", "role")
    search_fields = ("user__email", "role__name")
