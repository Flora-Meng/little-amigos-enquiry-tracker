from django.contrib import admin

from .models import PartyMenuItem, PartySummary


class PartyMenuItemInline(admin.TabularInline):
    model = PartyMenuItem
    extra = 0


@admin.register(PartySummary)
class PartySummaryAdmin(admin.ModelAdmin):
    list_display = ("party_date", "party_time", "owner_name", "location", "room_type", "updated_at")
    search_fields = ("owner_name", "owner_number", "kids_name", "theme")
    list_filter = ("location", "room_type", "party_date")
    inlines = (PartyMenuItemInline,)
