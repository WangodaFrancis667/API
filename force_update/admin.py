from django.contrib import admin
from .models import ForceUpdateConfig

@admin.register(ForceUpdateConfig)
class ForceUpdateConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "latest_version_name", "latest_version_code", "minimum_required_version_code", "force_update", "updated_at")
    readonly_fields = ("updated_at",)
    search_fields = ("name", "latest_version_name")
