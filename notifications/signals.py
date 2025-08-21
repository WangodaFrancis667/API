from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import InAppNotifications
from .services import _invalidate_user_cache

@receiver(post_save, sender=InAppNotifications)
def _notif_saved(sender, instance: InAppNotifications, **kwargs):
    _invalidate_user_cache(instance.user_id, instance.user_type)

@receiver(post_delete, sender=InAppNotifications)
def _notif_deleted(sender, instance: InAppNotifications, **kwargs):
    _invalidate_user_cache(instance.user_id, instance.user_type)