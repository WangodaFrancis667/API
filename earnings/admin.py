from django.contrib import admin
from .models import VendorEarnings, VendorPayout, VendorEarningSummary


@admin.register(VendorEarnings)
class VendorEarningsAdmin(admin.ModelAdmin):
    list_display = [
        "vendor",
        "order",
        "gross_amount",
        "commission_amount",
        "net_earnings",
        "status",
        "created_at",
    ]
    list_filter = ["status", "created_at", "vendor"]
    search_fields = ["vendor__username", "vendor__business_name", "order__id"]
    readonly_fields = ["commission_amount", "net_earnings", "created_at"]

    fieldsets = (
        ("Basic Information", {"fields": ("vendor", "order")}),
        (
            "Financial Details",
            {
                "fields": (
                    "gross_amount",
                    "commission_rate",
                    "commission_amount",
                    "net_earnings",
                )
            },
        ),
        ("Status & Dates", {"fields": ("status", "processed_at", "paid_at")}),
    )

    def has_delete_permission(self, request, obj=None):
        # Only allow deletion if not yet paid
        if obj and obj.status == VendorEarnings.STATUS_PAID:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(VendorPayout)
class VendorPayoutAdmin(admin.ModelAdmin):
    list_display = [
        "vendor",
        "amount",
        "payout_method",
        "status",
        "reference_number",
        "created_at",
    ]
    list_filter = ["status", "payout_method", "created_at", "vendor"]
    search_fields = ["vendor__username", "vendor__business_name", "reference_number"]

    fieldsets = (
        ("Basic Information", {"fields": ("vendor", "amount", "payout_method")}),
        ("Status & Reference", {"fields": ("status", "reference_number", "notes")}),
        ("Dates", {"fields": ("processed_at",)}),
    )

    readonly_fields = ["created_at"]


@admin.register(VendorEarningSummary)
class VendorEarningSummaryAdmin(admin.ModelAdmin):
    list_display = [
        "vendor",
        "year",
        "month",
        "total_orders",
        "gross_sales",
        "net_earnings",
        "updated_at",
    ]
    list_filter = ["year", "month", "vendor"]
    search_fields = ["vendor__username", "vendor__business_name"]
    readonly_fields = ["created_at", "updated_at"]

    def has_add_permission(self, request):
        # These should be auto-generated
        return False
