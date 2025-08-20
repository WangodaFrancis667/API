from rest_framework import serializers
from django.conf import settings
from .models import Categories, Products, ProductImage, ProductMetaData

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


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image_url"]


class ProductsSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Products
        fields = [
            "id", "vendor_id", "title", "description",
            "regular_price", "group_price", "min_quantity",
            "unit", "category", "created_by_admin",
            "created_at", "updated_at", "images"
        ]


# Product meta data serializer
class ProductMetaDataSerializer(serializers.Serializer):
    class Meta:
        model = ProductMetaData
        fields = "__all__"