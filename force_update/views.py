from datetime import date
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ForceUpdateConfig
from .serializers import ForceUpdateSerializer
from .tasks import record_force_check  # optional background logging

CACHE_KEY = "force_update:config:production"
CACHE_TIMEOUT = getattr(settings, "FORCE_UPDATE_CACHE_TIMEOUT", 60)  # seconds

# Helper: compute response
def _compute_update_response(cfg, current_build_number: int, current_version: str, test_scenario: str):
    minimum_required_version_code = cfg.minimum_required_version_code
    latest_version_name = cfg.latest_version_name
    latest_version_code = cfg.latest_version_code
    force_update_enabled = cfg.force_update
    soft_update_version_code = cfg.soft_update_version_code or (minimum_required_version_code - 1)
    play_store_url = cfg.play_store_url or getattr(settings, "PLAY_STORE_URL", "")

    update_required = False
    is_force_update = False
    update_type = "none"

    if current_build_number > 0:
        if current_build_number < minimum_required_version_code:
            update_required = True
            is_force_update = force_update_enabled
            update_type = "force" if force_update_enabled else "recommended"
        elif current_build_number < soft_update_version_code:
            update_required = True
            is_force_update = False
            update_type = "optional"
        elif current_build_number < latest_version_code:
            update_required = True
            is_force_update = False
            update_type = "available"
    # messages
    messages = {
        "force": "Critical update required! This version of AfroBuy is no longer supported. Please update immediately to continue using the app.",
        "recommended": "Important update available! Please update AfroBuy to get the latest features and security improvements.",
        "optional": "New version available! Update AfroBuy to get the latest features and improvements.",
        "available": "Latest version available with new features and improvements.",
        "none": "You're using the latest version of AfroBuy!",
    }
    update_message = messages.get(update_type, messages["none"])

    response = {
        "minimum_required_version_code": minimum_required_version_code,
        "latest_version_name": latest_version_name,
        "latest_version_code": latest_version_code,
        "force_update": is_force_update,
        "update_message": update_message,
        "play_store_url": play_store_url,
        "update_required": update_required,
        "update_type": update_type,
        "current_version_supported": not is_force_update,
        "soft_update_threshold": soft_update_version_code,
        # backward compatibility
        "version": latest_version_name,
        "build": latest_version_code,
        "store_url": play_store_url,
        "min_required_version": latest_version_name,
        "update_date": date.today().isoformat(),
        "update_available": update_required,
        "debug_info": {
            "test_scenario": test_scenario or "production",
            "current_app_version": current_version,
            "current_build_number": current_build_number,
            "platform": "android",
            "timestamp": date.today().isoformat(),
            "comparison_result": {
                "is_below_minimum": current_build_number < minimum_required_version_code,
                "is_below_soft_threshold": current_build_number < soft_update_version_code,
                "is_below_latest": current_build_number < latest_version_code,
            }
        },
        "api_version": "2.0",
        "status": "success",
    }
    return response


class ForceUpdateView(APIView):
    """
    Endpoint: GET /api/force-update/
    Returns a JSON response indicating whether the client must/should update.
    Query parameters:
      - current_version or app_version
      - current_build or build_number
      - test_force_update / test_optional_update / test_no_update (flags)
    """

    permission_classes = []  # public endpoint
    throttle_scope = "anon"  # consider rate-limiting if needed

    def get(self, request, *args, **kwargs):
        serializer = ForceUpdateSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Decide test scenario
        test_scenario = ""
        if data.get("test_force_update"):
            test_scenario = "force_update"
        elif data.get("test_optional_update"):
            test_scenario = "optional_update"
        elif data.get("test_no_update"):
            test_scenario = "no_update"

        # load config (cache for speed)
        cfg = cache.get(CACHE_KEY)
        if not cfg:
            # ensure there is a production config; otherwise fallback to defaults
            try:
                cfg = ForceUpdateConfig.objects.get(name="production")
            except ForceUpdateConfig.DoesNotExist:
                # Build ephemeral default config
                cfg = ForceUpdateConfig(
                    name="production",
                    minimum_required_version_code=getattr(settings, "MIN_REQUIRED_VERSION_CODE", 1),
                    latest_version_name=getattr(settings, "LATEST_VERSION_NAME", "1.0.7"),
                    latest_version_code=getattr(settings, "LATEST_VERSION_CODE", 1),
                    force_update=getattr(settings, "FORCE_UPDATE_ENABLED", False),
                    soft_update_version_code=getattr(settings, "SOFT_UPDATE_VERSION_CODE", None),
                    play_store_url=getattr(settings, "PLAY_STORE_URL", ""),
                )
            cache.set(CACHE_KEY, cfg, CACHE_TIMEOUT)

        # If test scenario requested, we allow temporary overrides
        current_build_number = int(request.query_params.get("build_number") or request.query_params.get("current_build") or 0)
        current_version = request.query_params.get("app_version") or request.query_params.get("current_version") or ""

        # allow explicit simulation of build via test flags (mirrors your PHP logic)
        if test_scenario:
            ts = {
                "force_update": dict(minimum_required_version_code=cfg.minimum_required_version_code,
                                     latest_version_name=cfg.latest_version_name,
                                     latest_version_code=cfg.latest_version_code,
                                     force_update=cfg.force_update,
                                     current_build_simulation=cfg.latest_version_code),
                "optional_update": dict(minimum_required_version_code=cfg.minimum_required_version_code,
                                        latest_version_name=cfg.latest_version_name,
                                        latest_version_code=cfg.latest_version_code,
                                        force_update=False,
                                        current_build_simulation=max(0, (cfg.soft_update_version_code or cfg.minimum_required_version_code) - 1)),
                "no_update": dict(minimum_required_version_code=cfg.minimum_required_version_code,
                                  latest_version_name=cfg.latest_version_name,
                                  latest_version_code=cfg.latest_version_code,
                                  force_update=False,
                                  current_build_simulation=cfg.latest_version_code),
            }.get(test_scenario)

            current_build_number = ts["current_build_simulation"]

        # compute response
        response = _compute_update_response(cfg, current_build_number, current_version, test_scenario)

        # optionally fire an async task that logs the check (non-blocking)
        try:
            record_force_check.delay({
                "current_build": current_build_number,
                "current_version": current_version,
                "client_ip": request.META.get("REMOTE_ADDR", ""),
                "test_scenario": test_scenario,
                "timestamp": response["debug_info"]["timestamp"],
            })
        except Exception:
            # if celery missing just pass
            pass

        # If no custom query flags and no explicit build param, provide testing instructions
        if not test_scenario and current_build_number == 0:
            response["testing_instructions"] = {
                "force_update_test": "?test_force_update=true",
                "optional_update_test": "?test_optional_update=true",
                "no_update_test": "?test_no_update=true",
                "custom_test": "?current_version=1.0.4&current_build=8",
                "note": "Add these parameters to the URL to test different scenarios"
            }

        return Response(response, status=status.HTTP_200_OK)
