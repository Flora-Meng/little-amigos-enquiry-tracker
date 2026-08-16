from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Location, User


@admin.register(User)
class LittleAmigosUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "display_name", "role", "location", "is_active")
    list_filter = ("role", "location", "is_active")
    search_fields = ("email", "display_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("display_name", "role", "location")}),
        ("Security", {"fields": ("password_reset_required", "is_active")}),
        ("Admin access", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "role", "location", "password1", "password2"),
            },
        ),
    )
    readonly_fields = ("last_login",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "timezone")
