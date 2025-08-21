from rest_framework import serializers
from .models import InAppNotifications, NotificationTypes, UserTypes

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotifications
        fields = [
            'id', 'type', 'title', 'message', 'otp_code', 'is_read',
            'is_urgent', 'created_at', 'expires_at'
        ]

class CreateCustomNotificationSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField()
    user_type = serializers.ChoiceField(choices=UserTypes.choices)
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    is_urgent = serializers.BooleanField(default=False)
    expires_minutes = serializers.IntegerField(required=False, min_value=1)
    type = serializers.ChoiceField(choices=NotificationTypes.choices, default=NotificationTypes.GENERAL)

class MarkReadSerializer(serializers.Serializer):
    notification_id = serializers.IntegerField()

class PhoneQuerySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    unread_only = serializers.BooleanField(default=False)
    limit = serializers.IntegerField(default=10, min_value=1, max_value=100)