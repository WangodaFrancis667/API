# notifications/admin.py
from django.contrib import admin
from .models import InAppNotifications

@admin.register(InAppNotifications)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'user_type', 'type', 'title', 'is_read', 'is_urgent', 'created_at', 'expires_at')
    list_filter = ('user_type', 'type', 'is_read', 'is_urgent', 'created_at')
    search_fields = ('title', 'message', 'otp_code', 'phone', 'user__email', 'user__username')
