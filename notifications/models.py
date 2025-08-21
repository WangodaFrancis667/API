from django.db import models
from django.conf import settings
from django.utils import timezone

class UserTypes(models.TextChoices):
    BUYER = 'buyer', 'Buyer'
    VENDOR = 'vendor', 'Vendor'

class NotificationTypes(models.TextChoices):
    OTP_PASSWORD_RESET = 'otp_password_reset', 'OTP Password Reset'
    OTP_VERIFICATION   = 'otp_verification', 'OTP Verification'
    GENERAL            = 'general', 'General'
    ORDER_CREATED      = 'order_created', 'Order Created'   # for vendors
    ORDER_UPDATE       = 'order_update', 'Order Update'     # for buyers
    PAYMENT_UPDATE     = 'payment_update', 'Payment Update'
    APP_UPDATE         = 'app_update', 'App Update'


# In-app notifictaion model
class InAppNotifications(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    user_type = models.CharField(max_length=12, choices=UserTypes.choices)
    phone = models.CharField(max_length=20)

    type = models.CharField(max_length=32, choices=NotificationTypes.choices, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()

    otp_code = models.CharField(max_length=6, null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    is_urgent = models.BooleanField(default=False)

    # optional metadata for advanced use-cases
    metadata = models.JSONField(null=True, blank=True)

    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'user_type']),
            models.Index(fields=['phone']),
            models.Index(fields=['type', 'is_read']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-is_urgent', '-created_at']

    def __str__(self):
        return f"[{self.type}] {self.title} -> {self.user_id}"

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())


