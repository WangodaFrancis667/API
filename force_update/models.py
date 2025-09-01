from django.db import models
from django.utils import timezone

class ForceUpdateConfig(models.Model):
    """
    Central configuration that defines latest version info and thresholds.
    You can change these in admin or via data migrations. For temporary test scenarios
    we support query params that override the production configuration.
    """
    name = models.CharField(max_length=100, default="production", unique=True)
    minimum_required_version_code = models.PositiveIntegerField(default=1)
    latest_version_name = models.CharField(max_length=50, default="1.0.7")
    latest_version_code = models.PositiveIntegerField(default=1)
    force_update = models.BooleanField(default=False)
    soft_update_version_code = models.PositiveIntegerField(null=True, blank=True)  # optional
    play_store_url = models.URLField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Force Update Configuration"
        verbose_name_plural = "Force Update Configurations"

    def __str__(self):
        return f"{self.name}: v{self.latest_version_name} ({self.latest_version_code})"
