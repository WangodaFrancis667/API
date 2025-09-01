from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def record_force_check(self, payload: dict):
    """
    Optional task to record checks for telemetry / analytics.
    Keep this simple (write to remote telemetry, push to analytics, or log to DB).
    """
    try:
        # example: simply log - replace with real telemetry
        logger.info("Force update check: %s", payload)
        return True
    except Exception as exc:
        logger.exception("Failed to record_force_check")
        raise self.retry(exc=exc, countdown=10)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def fetch_store_versions_task(self, config_id: int):
    """
    Asynchronous task to fetch version information from app stores and update configuration.

    Args:
        config_id: ID of the ForceUpdateConfig to update
    """
    try:
        from .models import ForceUpdateConfig
        from .services import get_store_service

        # Get the configuration
        try:
            config = ForceUpdateConfig.objects.get(id=config_id)
        except ForceUpdateConfig.DoesNotExist:
            logger.error(f"ForceUpdateConfig with id {config_id} not found")
            return False

        store_service = get_store_service()
        updated = False

        # Fetch Android version information
        if config.android_package_id:
            logger.info(
                f"Fetching Google Play Store info for package: {config.android_package_id}"
            )
            android_info, error = store_service.get_google_play_version(
                config.android_package_id
            )

            if android_info:
                if android_info.get("version_name"):
                    old_version = config.latest_version_name
                    config.latest_version_name = android_info["version_name"]

                    if old_version != config.latest_version_name:
                        logger.info(
                            f"Updated Android version: {old_version} -> {config.latest_version_name}"
                        )
                        updated = True

                if android_info.get("version_code"):
                    old_code = config.latest_version_code
                    config.latest_version_code = android_info["version_code"]

                    if old_code != config.latest_version_code:
                        logger.info(
                            f"Updated Android version code: {old_code} -> {config.latest_version_code}"
                        )
                        updated = True
            elif error:
                logger.warning(f"Failed to fetch Android version info: {error}")

        # Fetch iOS version information
        if config.ios_app_id:
            logger.info(f"Fetching App Store info for app ID: {config.ios_app_id}")
            ios_info, error = store_service.get_app_store_version(
                config.ios_app_id, config.ios_bundle_id
            )

            if ios_info:
                if ios_info.get("version_name"):
                    old_version = config.ios_latest_version_name
                    config.ios_latest_version_name = ios_info["version_name"]

                    if old_version != config.ios_latest_version_name:
                        logger.info(
                            f"Updated iOS version: {old_version} -> {config.ios_latest_version_name}"
                        )
                        updated = True

                # Update App Store URL if available
                if ios_info.get("app_store_url"):
                    old_url = config.app_store_url
                    config.app_store_url = ios_info["app_store_url"]

                    if old_url != config.app_store_url:
                        logger.info(f"Updated App Store URL")
                        updated = True
            elif error:
                logger.warning(f"Failed to fetch iOS version info: {error}")

        # Update the last check timestamp
        config.last_store_check = timezone.now()

        # Save the configuration if any changes were made
        if (
            updated or not config.pk
        ):  # Save if updated or if this is a new unsaved instance
            config.save()
            logger.info(
                f"Store version check completed for config {config_id}. Updated: {updated}"
            )
        else:
            # Still update the timestamp even if no version changes
            config.save(update_fields=["last_store_check"])
            logger.info(
                f"Store version check completed for config {config_id}. No version changes."
            )

        return True

    except Exception as exc:
        logger.exception(f"Failed to fetch store versions for config {config_id}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True)
def periodic_store_check(self):
    """
    Periodic task to check store versions for all configurations that have auto-fetch enabled.
    This should be scheduled to run regularly (e.g., every hour or daily).
    """
    try:
        from .models import ForceUpdateConfig
        from datetime import timedelta
        from django.db import models

        # Find configurations that need store checks
        cutoff_time = timezone.now() - timedelta(
            hours=1
        )  # Check configs not updated in the last hour

        configs_to_check = ForceUpdateConfig.objects.filter(
            auto_fetch_store_info=True
        ).filter(
            models.Q(last_store_check__isnull=True)
            | models.Q(last_store_check__lt=cutoff_time)
        )

        for config in configs_to_check:
            logger.info(
                f"Scheduling store check for config: {config.name} (ID: {config.id})"
            )
            # Schedule the fetch task with a delay to avoid overwhelming the APIs
            fetch_store_versions_task.apply_async(args=[config.id], countdown=10)

        return f"Scheduled store checks for {configs_to_check.count()} configurations"

    except Exception as exc:
        logger.exception("Failed to schedule periodic store checks")
        return f"Failed: {str(exc)}"


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def manual_store_version_update(
    self, platform: str, package_id: str = None, app_id: str = None
):
    """
    Manual task to update store version information for a specific platform and app.

    Args:
        platform: 'android' or 'ios'
        package_id: Android package ID (required for Android)
        app_id: iOS App Store ID (required for iOS)
    """
    try:
        from .services import get_store_service

        store_service = get_store_service()
        result = {"platform": platform, "success": False, "data": None, "error": None}

        if platform == "android" and package_id:
            info, error = store_service.get_google_play_version(package_id)
            result.update({"data": info, "error": error, "success": info is not None})

        elif platform == "ios" and app_id:
            info, error = store_service.get_app_store_version(app_id)
            result.update({"data": info, "error": error, "success": info is not None})

        else:
            result["error"] = f"Invalid parameters for platform {platform}"

        logger.info(f"Manual store version update result: {result}")
        return result

    except Exception as exc:
        logger.exception(f"Failed manual store version update for {platform}")
        raise self.retry(exc=exc, countdown=30)
