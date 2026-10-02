from django.contrib import admin

from .models import PartyIntakeLink, PartyMenuItem, PartySummary


class PartyMenuItemInline(admin.TabularInline):
    model = PartyMenuItem
    extra = 0


@admin.register(PartySummary)
class PartySummaryAdmin(admin.ModelAdmin):
    list_display = ("party_date", "party_time", "owner_name", "location", "room_type", "updated_at")
    search_fields = ("owner_name", "owner_number", "kids_name", "theme")
    list_filter = ("location", "room_type", "party_date")
    inlines = (PartyMenuItemInline,)


@admin.register(PartyIntakeLink)
class PartyIntakeLinkAdmin(admin.ModelAdmin):
    list_display = ("owner_name", "location", "submitted_at", "created_at")
    search_fields = ("owner_name", "owner_number", "owner_email")
    list_filter = ("location", "submitted_at")
