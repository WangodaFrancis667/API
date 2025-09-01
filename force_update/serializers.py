from rest_framework import serializers
from .models import ForceUpdateConfig


class ForceUpdateSerializer(serializers.Serializer):
    # Input fields (optional overrides)
    platform = serializers.CharField(required=False, default="android")
    current_version = serializers.CharField(required=False, allow_blank=True)
    current_build = serializers.IntegerField(required=False, min_value=0)
    test_force_update = serializers.BooleanField(required=False, default=False)
    test_optional_update = serializers.BooleanField(required=False, default=False)
    test_no_update = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = ForceUpdateConfig
        fields = "__all__"
