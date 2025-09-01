from django.contrib import admin
from .models import ForceUpdateConfig, StoreVersionCheck


@admin.register(ForceUpdateConfig)
class ForceUpdateConfigAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "platform",
        "latest_version_name",
        "latest_version_code",
        "ios_latest_version_name",
        "ios_latest_build_number",
        "minimum_required_version_code",
        "force_update",
        "auto_fetch_store_info",
        "updated_at",
    )
    list_filter = ("platform", "force_update", "auto_fetch_store_info", "updated_at")
    readonly_fields = ("updated_at", "last_store_check")
    search_fields = (
        "name",
        "latest_version_name",
        "android_package_id",
        "ios_bundle_id",
    )

    fieldsets = (
        (
            "Basic Configuration",
            {"fields": ("name", "platform", "force_update", "updated_at")},
        ),
        (
            "Android Settings",
            {
                "fields": (
                    "minimum_required_version_code",
                    "latest_version_name",
                    "latest_version_code",
                    "soft_update_version_code",
                    "play_store_url",
                    "android_package_id",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "iOS Settings",
            {
                "fields": (
                    "ios_minimum_required_build",
                    "ios_latest_version_name",
                    "ios_latest_build_number",
                    "ios_soft_update_build",
                    "app_store_url",
                    "ios_app_id",
                    "ios_bundle_id",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Store Integration",
            {
                "fields": (
                    "auto_fetch_store_info",
                    "store_check_interval_hours",
                    "last_store_check",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["trigger_store_version_check"]

    def trigger_store_version_check(self, request, queryset):
        """Admin action to trigger store version checks for selected configurations."""
        from .tasks import fetch_store_versions_task

        for config in queryset:
            if config.auto_fetch_store_info:
                fetch_store_versions_task.delay(config.id)

        self.message_user(
            request,
            f"Store version check triggered for {queryset.count()} configurations.",
        )

    trigger_store_version_check.short_description = "Trigger store version check"


@admin.register(StoreVersionCheck)
class StoreVersionCheckAdmin(admin.ModelAdmin):
    list_display = (
        "platform",
        "app_id",
        "version_name",
        "version_code",
        "build_number",
        "status",
        "checked_at",
    )
    list_filter = ("platform", "status", "checked_at")
    readonly_fields = ("checked_at",)
    search_fields = ("app_id", "version_name")
    ordering = ("-checked_at",)

    # Make this read-only since it's primarily for monitoring
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
