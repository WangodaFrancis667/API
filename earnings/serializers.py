from rest_framework import serializers
from django.contrib.auth import get_user_model

from orders.models import Order
from .models import VendorEarnings, VendorPayout, VendorEarningSummary

User = get_user_model()


class VendorSerializer(serializers.ModelSerializer):
    """Serializer for vendor basic info"""

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "business_name", "email", "phone"]


class OrderSerializer(serializers.ModelSerializer):
    vendor_info = VendorSerializer(source="vendor", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "total_amount",
            "payment_method",
            "status",
            "created_at",
            "vendor_info",
        ]


class VendorEarningsSerializer(serializers.ModelSerializer):
    vendor_info = VendorSerializer(source="vendor", read_only=True)
    order_info = OrderSerializer(source="order", read_only=True)

    class Meta:
        model = VendorEarnings
        fields = [
            "id",
            "gross_amount",
            "commission_rate",
            "commission_amount",
            "net_earnings",
            "status",
            "created_at",
            "processed_at",
            "paid_at",
            "vendor_info",
            "order_info",
        ]


class VendorPayoutSerializer(serializers.ModelSerializer):
    vendor_info = VendorSerializer(source="vendor", read_only=True)

    class Meta:
        model = VendorPayout
        fields = [
            "id",
            "amount",
            "payout_method",
            "status",
            "reference_number",
            "notes",
            "created_at",
            "processed_at",
            "vendor_info",
        ]


class VendorEarningSummarySerializer(serializers.ModelSerializer):
    vendor_info = VendorSerializer(source="vendor", read_only=True)

    class Meta:
        model = VendorEarningSummary
        fields = [
            "id",
            "year",
            "month",
            "total_orders",
            "gross_sales",
            "total_commission",
            "net_earnings",
            "vendor_info",
        ]


class VendorBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["wallet"]
