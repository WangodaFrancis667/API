from django.contrib import admin
from .models import AppSettings

# Register your models here.
@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "setting_key", "setting_value", "created_at", "updated_at")
    search_fields = ("setting_key",)
    list_filter = ("setting_value", "created_at")
