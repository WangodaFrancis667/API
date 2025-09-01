from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
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
