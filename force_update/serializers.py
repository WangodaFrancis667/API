from rest_framework import serializers
from .models import ForceUpdateConfig, StoreVersionCheck


class ForceUpdateSerializer(serializers.Serializer):
    # Input fields (optional overrides)
    platform = serializers.ChoiceField(
        choices=["android", "ios"],
        required=False,
        default="android",
        help_text="Platform: android or ios",
    )
    current_version = serializers.CharField(required=False, allow_blank=True)
    current_build = serializers.IntegerField(required=False, min_value=0)
    build_number = serializers.IntegerField(
        required=False, min_value=0
    )  # alias for current_build
    app_version = serializers.CharField(
        required=False, allow_blank=True
    )  # alias for current_version

    # Test scenario flags
    test_force_update = serializers.BooleanField(required=False, default=False)
    test_optional_update = serializers.BooleanField(required=False, default=False)
    test_no_update = serializers.BooleanField(required=False, default=False)

    # Store update flags
    fetch_from_store = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Whether to fetch latest version from app stores",
    )

    def validate(self, attrs):
        # Handle aliases
        if "build_number" in attrs and "current_build" not in attrs:
            attrs["current_build"] = attrs["build_number"]
        if "app_version" in attrs and "current_version" not in attrs:
            attrs["current_version"] = attrs["app_version"]

        return attrs


class ForceUpdateConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForceUpdateConfig
        fields = "__all__"


class StoreVersionCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreVersionCheck
        fields = "__all__"
        read_only_fields = ["checked_at"]


class ForceUpdateResponseSerializer(serializers.Serializer):
    """Serializer for the force update response structure."""

    # Common fields
    platform = serializers.CharField()
    update_required = serializers.BooleanField()
    force_update = serializers.BooleanField()
    update_type = serializers.CharField()
    update_message = serializers.CharField()
    current_version_supported = serializers.BooleanField()

    # Android specific fields
    minimum_required_version_code = serializers.IntegerField(required=False)
    latest_version_name = serializers.CharField(required=False)
    latest_version_code = serializers.IntegerField(required=False)
    soft_update_threshold = serializers.IntegerField(required=False)
    play_store_url = serializers.URLField(required=False)

    # iOS specific fields
    ios_minimum_required_build = serializers.IntegerField(required=False)
    ios_latest_version_name = serializers.CharField(required=False)
    ios_latest_build_number = serializers.IntegerField(required=False)
    ios_soft_update_build = serializers.IntegerField(required=False)
    app_store_url = serializers.URLField(required=False)

    # Backward compatibility fields
    version = serializers.CharField(required=False)
    build = serializers.IntegerField(required=False)
    store_url = serializers.URLField(required=False)
    min_required_version = serializers.CharField(required=False)

    # Meta fields
    update_date = serializers.DateField()
    update_available = serializers.BooleanField()
    api_version = serializers.CharField()
    status = serializers.CharField()

    # Debug information
    debug_info = serializers.DictField()
    testing_instructions = serializers.DictField(required=False)
