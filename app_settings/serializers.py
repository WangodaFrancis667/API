from rest_framework import serializers

from .models import AppSettings

class AppSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppSettings
        fields = [
            "id", "setting_key", "setting_value"
        ]
        read_only_fields = [ "created_at", "updated_at"]
