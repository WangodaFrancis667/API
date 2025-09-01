from datetime import date, timedelta
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ForceUpdateConfig, StoreVersionCheck
from .serializers import (
    ForceUpdateSerializer,
    ForceUpdateConfigSerializer,
    StoreVersionCheckSerializer,
)
from .services import get_store_service
from .tasks import record_force_check, fetch_store_versions_task

import logging

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "force_update:config"
CACHE_TIMEOUT = getattr(
    settings, "FORCE_UPDATE_CACHE_TIMEOUT", 300
)  # 5 minutes default


class ForceUpdateView(APIView):
    """
    Enhanced Force Update endpoint that supports both Android and iOS platforms.

    Endpoints:
    - GET /api/updates/force-update/ - Main force update check

    Query parameters:
    - platform: 'android' or 'ios' (default: android)
    - current_version or app_version: Current app version string
    - current_build or build_number: Current build/version code number
    - fetch_from_store: Whether to fetch latest info from stores (default: false)
    - test_force_update/test_optional_update/test_no_update: Test flags
    """

    permission_classes = []  # public endpoint
    throttle_scope = "anon"

    def get(self, request, *args, **kwargs):
        serializer = ForceUpdateSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        platform = data.get("platform", "android")
        fetch_from_store = data.get("fetch_from_store", False)

        # Decide test scenario
        test_scenario = self._determine_test_scenario(data)

        # Load or create configuration
        config = self._get_or_create_config(platform)

        # Always try to get fresh store data if it's stale or missing
        if self._should_fetch_from_store(config) or fetch_from_store:
            self._fetch_and_update_store_versions(config)
            # Reload config after potential updates
            config = self._get_or_create_config(platform, bypass_cache=True)

        # Extract client version info
        current_version = data.get("current_version", "")
        current_build = data.get("current_build", 0)

        # Apply test scenario overrides
        if test_scenario:
            current_build = self._apply_test_scenario(config, test_scenario, platform)

        # Compute response based on platform
        if platform == "ios":
            response = self._compute_ios_update_response(
                config, current_build, current_version, test_scenario
            )
        else:
            response = self._compute_android_update_response(
                config, current_build, current_version, test_scenario
            )

        # Add platform to response
        response["platform"] = platform

        # Log the check asynchronously
        self._log_force_check(
            request, current_build, current_version, platform, test_scenario, response
        )

        return Response(response, status=status.HTTP_200_OK)

    def _determine_test_scenario(self, data):
        """Determine which test scenario to apply."""
        if data.get("test_force_update"):
            return "force_update"
        elif data.get("test_optional_update"):
            return "optional_update"
        elif data.get("test_no_update"):
            return "no_update"
        return ""

    def _get_or_create_config(self, platform, bypass_cache=False):
        """Get or create force update configuration for the platform."""
        cache_key = f"{CACHE_KEY_PREFIX}:{platform}"

        if not bypass_cache:
            config = cache.get(cache_key)
            if config:
                return config

        try:
            config = ForceUpdateConfig.objects.get(
                name="production", platform__in=[platform, "universal"]
            )
        except ForceUpdateConfig.DoesNotExist:
            # Create default configuration
            config = self._create_default_config(platform)

        cache.set(cache_key, config, CACHE_TIMEOUT)
        return config

    def _create_default_config(self, platform):
        """Create default configuration for the platform."""
        defaults = {
            "name": "production",
            "platform": "universal",
            "minimum_required_version_code": getattr(
                settings, "MIN_REQUIRED_VERSION_CODE", 1
            ),
            "latest_version_name": getattr(settings, "LATEST_VERSION_NAME", "1.0.7"),
            "latest_version_code": getattr(settings, "LATEST_VERSION_CODE", 1),
            "force_update": getattr(settings, "FORCE_UPDATE_ENABLED", False),
            "play_store_url": getattr(settings, "PLAY_STORE_URL", ""),
            "android_package_id": getattr(settings, "ANDROID_PACKAGE_ID", ""),
        }

        if platform == "ios":
            defaults.update(
                {
                    "ios_minimum_required_build": getattr(
                        settings, "IOS_MIN_REQUIRED_BUILD", 1
                    ),
                    "ios_latest_version_name": getattr(
                        settings, "IOS_LATEST_VERSION_NAME", "1.0.7"
                    ),
                    "ios_latest_build_number": getattr(
                        settings, "IOS_LATEST_BUILD_NUMBER", 1
                    ),
                    "app_store_url": getattr(settings, "APP_STORE_URL", ""),
                    "ios_app_id": getattr(settings, "IOS_APP_ID", ""),
                    "ios_bundle_id": getattr(settings, "IOS_BUNDLE_ID", ""),
                }
            )

        return ForceUpdateConfig(**defaults)

    def _should_fetch_from_store(self, config):
        """Check if we should fetch version info from stores."""
        if not config.auto_fetch_store_info:
            return False

        if not config.last_store_check:
            return True

        time_since_check = timezone.now() - config.last_store_check
        return time_since_check >= timedelta(hours=config.store_check_interval_hours)

    def _fetch_and_update_store_versions(self, config):
        """Fetch version information from stores and update config."""
        try:
            # Use async task for better performance
            fetch_store_versions_task.delay(config.id)
        except Exception as e:
            logger.warning(f"Failed to trigger store version fetch task: {e}")
            # Fallback to synchronous fetch
            self._sync_fetch_store_versions(config)

    def _sync_fetch_store_versions(self, config):
        """Synchronously fetch and update store versions."""
        store_service = get_store_service()
        updated = False

        # Fetch Android version if configured
        if config.android_package_id:
            android_info, error = store_service.get_google_play_version(
                config.android_package_id
            )
            if android_info and android_info.get("version_name"):
                config.latest_version_name = android_info["version_name"]
                if android_info.get("version_code"):
                    config.latest_version_code = android_info["version_code"]
                updated = True

        # Fetch iOS version if configured
        if config.ios_app_id:
            ios_info, error = store_service.get_app_store_version(
                config.ios_app_id, config.ios_bundle_id
            )
            if ios_info and ios_info.get("version_name"):
                config.ios_latest_version_name = ios_info["version_name"]
                config.app_store_url = ios_info.get(
                    "app_store_url", config.app_store_url
                )
                updated = True

        if updated:
            config.last_store_check = timezone.now()
            if hasattr(config, "save"):  # Only save if it's a real model instance
                config.save()

    def _apply_test_scenario(self, config, test_scenario, platform):
        """Apply test scenario to simulate different update conditions."""
        if platform == "ios":
            latest_build = config.ios_latest_build_number or 1
            min_required = config.ios_minimum_required_build or 1
            soft_threshold = config.ios_soft_update_build or (min_required - 1)
        else:
            latest_build = config.latest_version_code
            min_required = config.minimum_required_version_code
            soft_threshold = config.soft_update_version_code or (min_required - 1)

        scenarios = {
            "force_update": max(0, min_required - 1),
            "optional_update": max(0, soft_threshold - 1),
            "no_update": latest_build,
        }

        return scenarios.get(test_scenario, 0)

    def _compute_android_update_response(
        self, config, current_build, current_version, test_scenario
    ):
        """Compute update response for Android platform."""
        minimum_required = config.minimum_required_version_code
        latest_version = config.latest_version_name
        latest_build = config.latest_version_code
        force_update_enabled = config.force_update
        soft_threshold = config.soft_update_version_code or (minimum_required - 1)
        store_url = config.play_store_url or getattr(settings, "PLAY_STORE_URL", "")

        update_required = False
        is_force_update = False
        update_type = "none"

        if current_build > 0:
            if current_build < minimum_required:
                update_required = True
                is_force_update = force_update_enabled
                update_type = "force" if force_update_enabled else "recommended"
            elif current_build < soft_threshold:
                update_required = True
                is_force_update = False
                update_type = "optional"
            elif current_build < latest_build:
                update_required = True
                is_force_update = False
                update_type = "available"

        return self._build_response(
            config,
            current_build,
            current_version,
            test_scenario,
            minimum_required,
            latest_version,
            latest_build,
            is_force_update,
            update_required,
            update_type,
            store_url,
            soft_threshold,
            "android",
        )

    def _compute_ios_update_response(
        self, config, current_build, current_version, test_scenario
    ):
        """Compute update response for iOS platform."""
        minimum_required = config.ios_minimum_required_build or 1
        latest_version = config.ios_latest_version_name or config.latest_version_name
        latest_build = config.ios_latest_build_number or 1
        force_update_enabled = config.force_update
        soft_threshold = config.ios_soft_update_build or (minimum_required - 1)
        store_url = config.app_store_url or getattr(settings, "APP_STORE_URL", "")

        update_required = False
        is_force_update = False
        update_type = "none"

        if current_build > 0:
            if current_build < minimum_required:
                update_required = True
                is_force_update = force_update_enabled
                update_type = "force" if force_update_enabled else "recommended"
            elif current_build < soft_threshold:
                update_required = True
                is_force_update = False
                update_type = "optional"
            elif current_build < latest_build:
                update_required = True
                is_force_update = False
                update_type = "available"

        return self._build_response(
            config,
            current_build,
            current_version,
            test_scenario,
            minimum_required,
            latest_version,
            latest_build,
            is_force_update,
            update_required,
            update_type,
            store_url,
            soft_threshold,
            "ios",
        )

    def _build_response(
        self,
        config,
        current_build,
        current_version,
        test_scenario,
        minimum_required,
        latest_version,
        latest_build,
        is_force_update,
        update_required,
        update_type,
        store_url,
        soft_threshold,
        platform,
    ):
        """Build a clean, professional response object with only essential information."""

        # Get the latest store data for this platform
        latest_store_data = self._get_latest_store_data(platform)

        # Use store data if available, otherwise fallback to config
        if latest_store_data:
            latest_version = latest_store_data.get("version_name", latest_version)
            if platform == "android" and latest_store_data.get("version_code"):
                latest_build = latest_store_data.get("version_code")

        messages = {
            "force": "Critical update required! Please update immediately to continue using the app.",
            "recommended": "Important update available! Please update to get the latest features and security improvements.",
            "optional": "New version available! Update to get the latest features and improvements.",
            "available": "Latest version available with new features and improvements.",
            "none": "You're using the latest version!",
        }

        update_message = messages.get(update_type, messages["none"])

        # Build clean response with only essential fields
        response = {
            "update_required": update_required,
            "force_update": is_force_update,
            "update_type": update_type,
            "update_message": update_message,
            "latest_version": latest_version,
            "latest_version_code": latest_build if platform == "android" else None,
            "latest_build_number": latest_build if platform == "ios" else None,
            "minimum_required_version_code": (
                minimum_required if platform == "android" else None
            ),
            "minimum_required_build_number": (
                minimum_required if platform == "ios" else None
            ),
            "store_url": store_url,
            "platform": platform,
        }

        # Remove null values to keep response clean
        response = {k: v for k, v in response.items() if v is not None}

        return response

    def _get_latest_store_data(self, platform):
        """Get the latest store version data from the database."""
        try:
            latest_check = (
                StoreVersionCheck.objects.filter(platform=platform, status="success")
                .order_by("-checked_at")
                .first()
            )

            if latest_check and latest_check.response_data:
                return latest_check.response_data
        except Exception as e:
            logger.warning(f"Failed to get latest store data for {platform}: {e}")

        return None

    def _get_testing_instructions(self, platform):
        """Get testing instructions for the platform."""
        base_instructions = {
            "force_update_test": f"?platform={platform}&test_force_update=true",
            "optional_update_test": f"?platform={platform}&test_optional_update=true",
            "no_update_test": f"?platform={platform}&test_no_update=true",
            "custom_test": f"?platform={platform}&current_version=1.0.4&current_build=8",
            "fetch_from_store": f"?platform={platform}&fetch_from_store=true",
            "note": "Add these parameters to the URL to test different scenarios",
        }

        if platform == "ios":
            base_instructions["custom_test"] = (
                f"?platform=ios&current_version=1.0.4&current_build=8"
            )

        return base_instructions

    def _log_force_check(
        self, request, current_build, current_version, platform, test_scenario, response
    ):
        """Log the force update check for analytics."""
        try:
            record_force_check.delay(
                {
                    "current_build": current_build,
                    "current_version": current_version,
                    "platform": platform,
                    "client_ip": request.META.get("REMOTE_ADDR", ""),
                    "test_scenario": test_scenario,
                    "timestamp": response["debug_info"]["timestamp"],
                    "update_required": response.get("update_required", False),
                    "update_type": response.get("update_type", "none"),
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log force update check: {e}")


class StoreVersionsView(APIView):
    """
    Endpoint to manually trigger store version checks and view recent checks.

    GET /api/updates/store-versions/ - List recent version checks
    POST /api/updates/store-versions/ - Trigger manual version check
    """

    permission_classes = []  # Consider adding authentication for POST requests

    def get(self, request):
        """Get recent store version checks."""
        checks = StoreVersionCheck.objects.all()[:20]
        serializer = StoreVersionCheckSerializer(checks, many=True)
        return Response(
            {
                "status": "success",
                "recent_checks": serializer.data,
                "total_checks": StoreVersionCheck.objects.count(),
            }
        )

    def post(self, request):
        """Manually trigger store version checks."""
        platform = request.data.get("platform", "both")

        store_service = get_store_service()
        results = {}

        try:
            config = ForceUpdateConfig.objects.get(name="production")

            if platform in ["android", "both"] and config.android_package_id:
                android_info, error = store_service.get_google_play_version(
                    config.android_package_id
                )
                results["android"] = {
                    "success": android_info is not None,
                    "data": android_info,
                    "error": error,
                }

            if platform in ["ios", "both"] and config.ios_app_id:
                ios_info, error = store_service.get_app_store_version(
                    config.ios_app_id, config.ios_bundle_id
                )
                results["ios"] = {
                    "success": ios_info is not None,
                    "data": ios_info,
                    "error": error,
                }

        except ForceUpdateConfig.DoesNotExist:
            return Response(
                {"status": "error", "message": "Force update configuration not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "status": "success",
                "message": "Store version check completed",
                "results": results,
            }
        )
