from django.db import transaction
from django.contrib.auth import get_user_model
from celery import shared_task, group
from django.utils import timezone

from .models import InAppNotifications, NotificationTypes, UserTypes
from .services import _invalidate_user_cache

User = get_user_model()

BATCH_SIZE = 1000

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def fanout_app_update_task(self, title: str, message: str, version: str = ""):
    """
    Creates APP_UPDATE notification for all users in batches.
    """
    q = User.objects.all().values('id')
    # simple batch iteration
    start = 0
    while True:
        batch = list(q[start:start+BATCH_SIZE])
        if not batch:
            break
        objs = []
        now = timezone.now()
        for row in batch:
            objs.append(InAppNotifications(
                user_id=row['id'],
                user_type=UserTypes.BUYER,   # if you store roles on user, you can map per-user; default to buyer
                phone=getattr(User.objects.filter(id=row['id']).first(), 'phone', '') or '',
                type=NotificationTypes.APP_UPDATE,
                title=title,
                message=f"{message}{(' — Version: ' + version) if version else ''}",
                is_urgent=True,
                created_at=now,
                updated_at=now,
            ))
            # You might enqueue separate vendor variant as needed

        with transaction.atomic():
            InAppNotifications.objects.bulk_create(objs, batch_size=1000)

        # Coarse cache invalidation for users in this batch
        for row in batch:
            _invalidate_user_cache(row['id'], UserTypes.BUYER)

        start += BATCH_SIZE


@shared_task
def warm_user_notification_cache_task(user_id: int, user_type: str):
    """
    Optional: call services.get_user_notifications to force-warm cache after heavy fan-out.
    """
    from .services import get_user_notifications
    class _U:  # tiny shim
        id = user_id
    get_user_notifications(user=_U, user_type=user_type, unread_only=False, limit=20)
