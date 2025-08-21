# notifications/services.py
from datetime import timedelta
from django.db import transaction, models
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings

from celery import shared_task

from .models import InAppNotifications, NotificationTypes, UserTypes
from .utils import invalidate_user_cache, CACHE_TTL, LIST_CACHE_KEY, COUNT_CACHE_KEY


def _enforce_visibility_rules(user_type: str, ntype: str) -> bool:
    """
    PHP logic parity:
    - Vendors: can see ORDER_CREATED + APP_UPDATE only
    - Buyers: can see ORDER_UPDATE, GENERAL, APP_UPDATE, PAYMENT_UPDATE
    - OTP excluded from normal feeds (handled in queries)
    """
    if user_type == UserTypes.VENDOR:
        return ntype in {NotificationTypes.ORDER_CREATED, NotificationTypes.APP_UPDATE}
    if user_type == UserTypes.BUYER:
        return ntype in {
            NotificationTypes.ORDER_UPDATE,
            NotificationTypes.GENERAL,
            NotificationTypes.APP_UPDATE,
            NotificationTypes.PAYMENT_UPDATE,
        }
    return False

# Deleting the otp
@transaction.atomic
def delete_otp_for_phone(phone: str):
    InAppNotifications.objects.filter(
        phone=phone,
        type__in=[NotificationTypes.OTP_PASSWORD_RESET, NotificationTypes.OTP_VERIFICATION]
    ).delete()

# Creating an otp verification
@transaction.atomic
def create_otp_notification(*, user, user_type: str, phone: str, otp_code: str, minutes_valid: int = 15):
    # Unique OTP per phone (like PHP)
    delete_otp_for_phone(phone)
    expires_at = timezone.now() + timedelta(minutes=minutes_valid)
    n = InAppNotifications.objects.create(
        user=user,
        user_type=user_type,
        phone=phone,
        type=NotificationTypes.OTP_PASSWORD_RESET,
        title="Password Reset Code",
        message=f"Your password reset verification code is: {otp_code}. "
                f"This code will expire in {minutes_valid} minutes. Do not share this code with anyone.",
        otp_code=otp_code,
        is_urgent=True,
        expires_at=expires_at,
    )
    invalidate_user_cache(user.id, user_type)
    return n

@transaction.atomic
def create_order_created_notification(*, user, user_type: str, phone: str, order_id: int, product_name: str):
    ntype = NotificationTypes.ORDER_CREATED
    # If accidentally called for buyer, coerce to ORDER_UPDATE (parity with PHP safety)
    if user_type == UserTypes.BUYER:
        ntype = NotificationTypes.ORDER_UPDATE

    n = InAppNotifications.objects.create(
        user=user,
        user_type=user_type,
        phone=phone,
        type=ntype,
        title="Order Created Successfully" if ntype == NotificationTypes.ORDER_CREATED else "Order Status Updated",
        message=f"Your order for {product_name} has been created successfully. Order ID: #{order_id}"
                if ntype == NotificationTypes.ORDER_CREATED
                else f"Your order status has been updated. Order ID: #{order_id} - {product_name}",
        is_urgent=False,
    )
    invalidate_user_cache(user.id, user_type)
    return n

@transaction.atomic
def create_order_update_notification(*, user, user_type: str, phone: str, order_id: int, new_status: str, product_name: str):
    status_titles = {
        'pending': 'Order Placed Successfully',
        'processing': 'Order Processing',
        'shipped': 'Order Shipped',
        'delivered': 'Order Delivered',
        'cancelled': 'Order Cancelled',
    }
    status_messages = {
        'pending': 'Your order is pending and will be processed soon.',
        'processing': 'Your order is being processed by the vendor.',
        'shipped': 'Great news! Your order has been shipped and is on its way.',
        'delivered': 'Your order has been delivered successfully.',
        'cancelled': 'Your order has been cancelled.',
    }
    is_urgent = new_status in {'shipped', 'delivered', 'cancelled'}
    n = InAppNotifications.objects.create(
        user=user,
        user_type=user_type,
        phone=phone,
        type=NotificationTypes.ORDER_UPDATE,
        title=status_titles.get(new_status, "Order Status Updated"),
        message=f"{status_messages.get(new_status, f'Your order status has been updated to {new_status}.')} "
                f"Order ID: #{order_id} - {product_name}",
        is_urgent=is_urgent,
    )
    invalidate_user_cache(user.id, user_type)
    return n

@transaction.atomic
def create_vendor_order_notification(*, vendor_user, vendor_phone: str, order_id: int, product_name: str, buyer_name: str, quantity: int):
    n = InAppNotifications.objects.create(
        user=vendor_user,
        user_type=UserTypes.VENDOR,
        phone=vendor_phone,
        type=NotificationTypes.ORDER_CREATED,
        title="New Order Received",
        message=f"You have a new order for {quantity}x {product_name} from {buyer_name}. Order ID: #{order_id}.",
        is_urgent=True,
    )
    invalidate_user_cache(vendor_user.id, UserTypes.VENDOR)
    return n

@transaction.atomic
def create_custom_notification(*, user, user_type: str, title: str, message: str, phone: str = "", metadata: dict | None = None,
                               is_urgent: bool = False, expires_at=None, ntype: str = NotificationTypes.GENERAL):
    # vendor restriction (only ORDER_CREATED) like PHP
    if user_type == UserTypes.VENDOR and ntype != NotificationTypes.ORDER_CREATED:
        return None

    # For “return_” metadata types force ORDER_UPDATE to ensure visibility
    if metadata and isinstance(metadata, dict):
        mtype = metadata.get('type', '')
        if isinstance(mtype, str) and mtype.startswith('return_'):
            ntype = NotificationTypes.ORDER_UPDATE

    n = InAppNotifications.objects.create(
        user=user,
        user_type=user_type,
        phone=phone or getattr(user, 'phone', '') or '',
        type=ntype,
        title=title,
        message=message,
        metadata=metadata or None,
        is_urgent=is_urgent,
        expires_at=expires_at
    )
    invalidate_user_cache(user.id, user_type)
    return n

def get_user_notifications(*, user, user_type: str, unread_only: bool = False, limit: int = 50, exclude_otp: bool = True):
    key = LIST_CACHE_KEY.format(uid=user.id, utype=user_type, unread=int(unread_only), limit=limit)
    cached = cache.get(key)
    if cached is not None:
        return cached, True

    qs = InAppNotifications.objects.filter(
        user=user,
        user_type=user_type,
    ).filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now()))

    if exclude_otp:
        qs = qs.exclude(type__in=[NotificationTypes.OTP_PASSWORD_RESET, NotificationTypes.OTP_VERIFICATION])

    # Strict separation logic:
    if user_type == UserTypes.VENDOR:
        qs = qs.filter(type__in=[NotificationTypes.ORDER_CREATED, NotificationTypes.APP_UPDATE])
    elif user_type == UserTypes.BUYER:
        qs = qs.filter(type__in=[NotificationTypes.ORDER_UPDATE, NotificationTypes.GENERAL,
                                 NotificationTypes.APP_UPDATE, NotificationTypes.PAYMENT_UPDATE])
    else:
        return [], False

    if unread_only:
        qs = qs.filter(is_read=False)

    data = list(qs.values(
        'id', 'type', 'title', 'message', 'otp_code', 'is_read', 'is_urgent', 'created_at', 'expires_at'
    )[:limit])

    cache.set(key, data, CACHE_TTL)
    return data, False

def get_notifications_by_phone(*, phone: str, unread_only: bool = False, limit: int = 10):
    qs = InAppNotifications.objects.filter(phone=phone).filter(
        models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
    )
    if unread_only:
        qs = qs.filter(is_read=False)
    return list(qs.values('id', 'type', 'title', 'message', 'otp_code', 'is_read',
                          'is_urgent', 'created_at', 'expires_at')[:limit])

def get_unread_count(*, user, user_type: str, exclude_otp: bool = True):
    key = COUNT_CACHE_KEY.format(uid=user.id, utype=user_type)
    cached = cache.get(key)
    if cached is not None:
        return cached, True

    qs = InAppNotifications.objects.filter(
        user=user,
        user_type=user_type,
        is_read=False
    ).filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now()))

    if exclude_otp:
        qs = qs.exclude(type__in=[NotificationTypes.OTP_PASSWORD_RESET, NotificationTypes.OTP_VERIFICATION])

    if user_type == UserTypes.VENDOR:
        qs = qs.filter(type__in=[NotificationTypes.ORDER_CREATED, NotificationTypes.APP_UPDATE])
    elif user_type == UserTypes.BUYER:
        qs = qs.filter(type__in=[NotificationTypes.ORDER_UPDATE, NotificationTypes.GENERAL,
                                 NotificationTypes.APP_UPDATE, NotificationTypes.PAYMENT_UPDATE])
    else:
        return 0, False

    count = qs.count()
    cache.set(key, count, CACHE_TTL)
    return count, False

@transaction.atomic
def mark_as_read(notification_id: int, *, user=None):
    updated = (InAppNotifications.objects
               .filter(id=notification_id)
               .filter(user=user) if user else InAppNotifications.objects.filter(id=notification_id)
               ).update(is_read=True)
    if user:
        invalidate_user_cache(user.id, getattr(user, 'role', '') or getattr(user, 'user_type', ''))
    return updated

@transaction.atomic
def mark_all_as_read(*, user, user_type: str):
    InAppNotifications.objects.filter(user=user, user_type=user_type, is_read=False).update(is_read=True)
    invalidate_user_cache(user.id, user_type)

def delete_expired_notifications():
    InAppNotifications.objects.filter(expires_at__lt=timezone.now()).delete()

def delete_notification(notification_id: int, *, user=None):
    qs = InAppNotifications.objects.filter(id=notification_id)
    if user:
        qs = qs.filter(user=user)
    obj = qs.first()
    if not obj:
        return 0
    uid, utype = obj.user_id, obj.user_type
    deleted, _ = qs.delete()
    invalidate_user_cache(uid, utype)
    return deleted

def delete_all_for_user(*, user, user_type: str):
    InAppNotifications.objects.filter(user=user, user_type=user_type).delete()
    invalidate_user_cache(user.id, user_type)

def create_app_update_for_all_users(title: str, message: str, version: str | None = None):
    """Direct implementation without Celery to avoid circular imports."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    notifications = []
    users_to_invalidate = []
    
    for user in User.objects.all():
        user_type = getattr(user, 'user_type', UserTypes.BUYER)
        notifications.append(InAppNotifications(
            user=user,
            user_type=user_type,
            phone=getattr(user, 'phone', ''),
            type=NotificationTypes.APP_UPDATE,
            title=title,
            message=message,
            is_urgent=False
        ))
        users_to_invalidate.append((user.id, user_type))
    
    if notifications:
        InAppNotifications.objects.bulk_create(notifications, batch_size=100)
        
        # Invalidate cache for all users
        for user_id, user_type in users_to_invalidate:
            invalidate_user_cache(user_id, user_type)


# def notify_vendor_new_order(vendor_id, order_id, product_name, buyer_id, quantity):
#     """
#     Send notification to vendor about new order
#     """
#     # TODO: Implement vendor notification logic
#     print(f"Vendor {vendor_id} has new order {order_id} for {product_name}")
#     pass



# def notify_buyer_status(buyer_id, order_id, status, product_name):
#     """
#     Send notification to buyer about order status change
#     """
#     # TODO: Implement buyer notification logic
#     print(f"Buyer {buyer_id} order {order_id} status: {status} for {product_name}")
#     pass


def _create(user_id:int, user_type:str, phone:str, type_:str, title:str, message:str, is_urgent=False, expires_at=None, otp_code=None):
    return InAppNotifications.objects.create(
        user_id=user_id, user_type=user_type, phone=phone, type=type_,
        title=title, message=message, is_urgent=is_urgent, expires_at=expires_at, otp_code=otp_code
    )



# These task wrappers are called from orders.services after DB commit
@shared_task
def notify_vendor_new_order(*, vendor_id:int, order_id:int, product_name:str, buyer_id:int, quantity:int):
    title = "New Order Received"
    msg = f"You have a new order for {quantity}x {product_name}. Order ID: #{order_id}."
    # You'll likely fetch vendor phone from your Vendors table
    phone = "0000000000"
    _create(user_id=vendor_id, user_type="vendor", phone=phone, type_="order_created",
            title=title, message=msg, is_urgent=True)

@shared_task
def notify_buyer_status(*, buyer_id:int, order_id:int, status:str, product_name:str):
    titles = {
        "pending":"Order Placed Successfully",
        "processing":"Order Processing",
        "shipped":"Order Shipped",
        "delivered":"Order Delivered",
        "cancelled":"Order Cancelled",
    }
    messages = {
        "pending":"Your order is pending and will be processed soon.",
        "processing":"Your order is being processed by the vendor.",
        "shipped":"Great news! Your order has been shipped and is on its way.",
        "delivered":"Your order has been delivered successfully.",
        "cancelled":"Your order has been cancelled.",
    }
    title = titles.get(status, "Order Status Updated")
    msg = f"{messages.get(status, f'Your order status has been updated to {status}.')} Order ID: #{order_id} - {product_name}"
    phone = "0000000000"  # fetch from Buyers table
    _create(user_id=buyer_id, user_type="buyer", phone=phone, type_="order_update",
            title=title, message=msg, is_urgent=(status in {"shipped","delivered","cancelled"}))
