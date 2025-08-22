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

"""
    This works with only images
"""
# This is the product image serializer
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image_url"]
        read_only_fields = ['id']

# Product image upload
class ProductImageUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading images to a specific product"""
    class Meta:
        model = ProductImage
        fields = ['product', 'image_url']
    
    def validate_product(self, value):
        # Ensure the product exists and is active
        if not value.is_active:
            raise serializers.ValidationError("Cannot add images to inactive products")
        return value
    
# Product with images serializer
class ProductWithImagesSerializer(serializers.ModelSerializer):
    """Product serializer that includes all images"""
    images = ProductImageSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Products
        fields = [
            'id', 'vendor', 'vendor_name', 'title', 'description', 'is_active',
            'regular_price', 'group_price', 'min_quantity', 'unit',
            'category', 'category_name', 'created_at', 'updated_at', 'images'
        ]
        read_only_fields = ['created_at', 'updated_at']

# Serializer for uploading bulky images at once
class BulkImageUploadSerializer(serializers.Serializer):
    """Serializer for uploading multiple images at once"""
    product_id = serializers.IntegerField()
    image_urls = serializers.ListField(
        child=serializers.CharField(max_length=255),
        min_length=1,
        max_length=10  # Limit to 10 images per upload
    )
    
    def validate_product_id(self, value):
        """Ensure the product exists"""
        try:
            product = Products.objects.get(id=value, is_active=True)
            return value
        except Products.DoesNotExist:
            raise serializers.ValidationError("Product not found or inactive")
    
    def validate_image_urls(self, value):
        """Basic validation for image URLs"""
        for url in value:
            if not url.strip():
                raise serializers.ValidationError("Image URL cannot be empty")
        return value


"""
    Product management serializers
"""
class ProductsSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.username', read_only=True)  # Add this line
    category_name = serializers.CharField(source='category.name', read_only=True)  # Add this line


    class Meta:
        model = Products
        fields = [
           'id', 'vendor', 'vendor_name', 'title', 'description', 'is_active',
            'regular_price', 'group_price', 'min_quantity', 'unit',
            'category', 'category_name', 'created_at', 'updated_at', 'images'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ProductMetaDataSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = ProductMetaData
        fields = [
            'id', 
            'type', 
            'type_display',
            'name', 
            'display_name',
            'description',
            'category_type',
            'is_active',
            'sort_order',
            'created_at',
            'updated_at'
        ]
        extra_kwargs = {
            'id': {'read_only': True}
        }
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data.pop('id', None)
        return super().create(validated_data)

    def validate_type(self, value):
        if value not in [choice[0] for choice in ProductMetaData.TypeChoices.choices]:
            raise serializers.ValidationError("Invalid type choice")
        return value

class ProductMetaDataListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views"""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = ProductMetaData
        fields = ['id', 'name', 'display_name', 'type', 'type_display', 'is_active', 'sort_order']
