from rest_framework import serializers
from django.conf import settings
from .models import Categories

class CategoriesSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Categories
        fields = ["id", "name", "description", "image_url", "is_active", "created_at", "updated_at"]

    def get_image_url(self, obj):
        # Ensure correct URL
        if obj.image_url:
            return f"{settings.MEDIA_URL}{obj.image_url}"
        return None
