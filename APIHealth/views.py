import psutil
import socket
import time
import platform
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

# Track app start time for uptime calculation
APP_START_TIME = time.time()


def get_uptime():
    """Return human-readable uptime since app start."""
    uptime_seconds = int(time.time() - APP_START_TIME)
    return str(timedelta(seconds=uptime_seconds))


def check_database():
    """Return True if default DB is reachable."""
    try:
        connections['default'].cursor()
        return True
    except OperationalError:
        return False


def check_redis():
    """Return True if Redis cache is reachable."""
    try:
        from django.core.cache import cache
        cache.set("health_check_ping", "pong", timeout=5)
        return cache.get("health_check_ping") == "pong"
    except Exception:
        return False


@csrf_exempt
def health_check(request):
    """
    Professional health check endpoint.
    - Returns JSON for API calls
    - Renders HTML if browser access
    """
    data = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "version": getattr(settings, "APP_VERSION", "1.0.0"),
        "site_name": getattr(settings, "SITE_NAME", "Afrobuy Team Uganda"),
        "server": socket.gethostname(),
        "python_version": platform.python_version(),
        "uptime": get_uptime(),
        "database_status": "online" if check_database() else "offline",
        "redis_status": "online" if check_redis() else "offline",
        "memory_usage": f"{psutil.virtual_memory().percent}%",
        "cpu_usage": f"{psutil.cpu_percent(interval=0.5)}%",
    }

    # If a monitoring tool wants JSON
    if request.headers.get("Accept") == "application/json":
        status_code = 200 if data["status"] == "healthy" else 503
        return JsonResponse(data, status=status_code)

    # Otherwise render the HTML template
    return render(request, "health_check.html", data)
