from django.db import models
from django.utils import timezone


class ForceUpdateConfig(models.Model):
    """
    Central configuration that defines latest version info and thresholds for different platforms.
    You can change these in admin or via data migrations. For temporary test scenarios
    we support query params that override the production configuration.
    """

    PLATFORM_CHOICES = [
        ("android", "Android"),
        ("ios", "iOS"),
        ("universal", "Universal (both platforms)"),
    ]

    name = models.CharField(max_length=100, default="production", unique=True)
    platform = models.CharField(
        max_length=20, choices=PLATFORM_CHOICES, default="universal"
    )

    # Android specific fields
    minimum_required_version_code = models.PositiveIntegerField(default=1)
    latest_version_name = models.CharField(max_length=50, default="1.0.7")
    latest_version_code = models.PositiveIntegerField(default=1)
    soft_update_version_code = models.PositiveIntegerField(null=True, blank=True)
    play_store_url = models.URLField(blank=True, null=True)
    android_package_id = models.CharField(
        max_length=255, blank=True, null=True, help_text="e.g. com.afrobuyug.app"
    )

    # iOS specific fields
    ios_minimum_required_build = models.PositiveIntegerField(null=True, blank=True)
    ios_latest_version_name = models.CharField(max_length=50, blank=True, null=True)
    ios_latest_build_number = models.PositiveIntegerField(null=True, blank=True)
    ios_soft_update_build = models.PositiveIntegerField(null=True, blank=True)
    app_store_url = models.URLField(blank=True, null=True)
    ios_app_id = models.CharField(
        max_length=50, blank=True, null=True, help_text="Apple App Store ID"
    )
    ios_bundle_id = models.CharField(
        max_length=255, blank=True, null=True, help_text="e.g. com.afrobuyug.app"
    )

    # Common fields
    force_update = models.BooleanField(default=False)
    auto_fetch_store_info = models.BooleanField(
        default=False, help_text="Automatically fetch latest version info from stores"
    )
    last_store_check = models.DateTimeField(null=True, blank=True)
    store_check_interval_hours = models.PositiveIntegerField(
        default=24, help_text="Hours between automatic store checks"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Force Update Configuration"
        verbose_name_plural = "Force Update Configurations"

    def __str__(self):
        if self.platform == "universal":
            return f"{self.name}: Android v{self.latest_version_name} ({self.latest_version_code}), iOS v{self.ios_latest_version_name or 'N/A'}"
        elif self.platform == "android":
            return f"{self.name} (Android): v{self.latest_version_name} ({self.latest_version_code})"
        else:
            return f"{self.name} (iOS): v{self.ios_latest_version_name or 'N/A'} ({self.ios_latest_build_number or 'N/A'})"


class StoreVersionCheck(models.Model):
    """
    Log of version checks from app stores for monitoring and debugging.
    """

    PLATFORM_CHOICES = [
        ("android", "Android (Google Play)"),
        ("ios", "iOS (App Store)"),
    ]

    STATUS_CHOICES = [
        ("success", "Success"),
        ("failed", "Failed"),
        ("rate_limited", "Rate Limited"),
        ("not_found", "Not Found"),
    ]

    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    app_id = models.CharField(
        max_length=255, help_text="Package ID for Android, App ID for iOS"
    )
    version_name = models.CharField(max_length=200, blank=True, null=True)
    version_code = models.PositiveIntegerField(null=True, blank=True)
    build_number = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    response_data = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Store Version Check"
        verbose_name_plural = "Store Version Checks"
        ordering = ["-checked_at"]

    def __str__(self):
        return f"{self.platform} - {self.app_id} - {self.status} ({self.checked_at})"
