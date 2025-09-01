from django.contrib import admin
from .models import Order, OrderItem, OrderReturn # GroupOrder, 

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id","user","vendor_id","status","total_amount","created_at")
    search_fields = ("id","user__username","group_id")
    list_filter = ("status",)

admin.site.register(OrderItem)
# admin.site.register(GroupOrder)
admin.site.register(OrderReturn)
