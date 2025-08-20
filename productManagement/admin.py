from django.contrib import admin
from django.utils.html import format_html
from .models import Categories, ProductMetaData, Products, ProductImage

@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "image_preview", "created_at", "updated_at")
    search_fields = ("name",)
    list_filter = ("is_active", "created_at")

    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="https://api.afrobuyug.com/{}" width="60" height="60" />', obj.image_url)
        return "-"
    image_preview.short_description = "Image"

@admin.register(ProductMetaData)
class ProductMetaDataAdmin(admin.ModelAdmin):
    list_display = ("id", "type", "name", "display_name", "description", "category_type", "sort_order", "is_active", "created_at", "updated_at")
    search_fields = ("name",)
    list_filter = ("is_active", "created_at")

@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ("id", "vendor", "title", "description", "is_active", "regular_price", "group_price", "min_quantity", "unit", "category", "created_at", "updated_at"  )
    search_fields = ("title",)
    list_filter = ("is_active", "created_at")

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "image_preview")
    search_fields = ("product",)
    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="https://api.afrobuyug.com/{}" width="60" height="60" />', obj.image_url)
        return "-"
    image_preview.short_description = "Image"