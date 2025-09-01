# Force Update Django App

Provides an endpoint at `/api/force-update/` that returns JSON telling clients whether they must update.

## Features
- Production configuration model editable via Django admin
- Query params for testing scenarios (mirrors your PHP script)
- Redis caching for fast responses
- Optional Celery task to record checks/telemetry
- Management command to run test queries locally
- Unit tests included

## Environment
- Add `force_update` to INSTALLED_APPS
- Configure CACHE (django-redis recommended) and Celery in your project settings:
  - `CACHES['default']['LOCATION'] = "redis://127.0.0.1:6379/1"`
  - `CELERY_BROKER_URL = "redis://127.0.0.1:6379/2"`
- Optional settings:
  - `FORCE_UPDATE_CACHE_TIMEOUT` (seconds)
  - `PLAY_STORE_URL`

## Endpoints
- `GET /api/force-update/` - returns JSON response
  - Query params:
    - `current_build` or `build_number`
    - `current_version` or `app_version`
    - `test_force_update=true` / `test_optional_update=true` / `test_no_update=true`
