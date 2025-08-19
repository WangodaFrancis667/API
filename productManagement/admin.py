from django.contrib import admin
from django.utils.html import format_html
from .models import Categories

@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "image_preview", "created_at", "updated_at")
    search_fields = ("name",)
    list_filter = ("is_active", "created_at")

    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="https://afrobuyug.com/{}" width="60" height="60" />', obj.image_url)
        return "-"
    image_preview.short_description = "Image"
