from rest_framework import serializers
from .models import Order, OrderItem

from rest_framework import serializers


class UpdateOrderStatusSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    new_status = serializers.ChoiceField(
        choices=[
            ("processing", "processing"),
            ("shipped", "shipped"),
            ("delivered", "delivered"),
            ("cancelled", "cancelled"),
        ]
    )


class OrderReturnCreateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    return_reason = serializers.CharField()


class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class OrderCreateSerializer(serializers.Serializer):
    buyer_id = serializers.IntegerField(min_value=1)  # maps to AUTH_USER_MODEL id
    vendor_id = serializers.IntegerField(min_value=1)
    payment_method = serializers.ChoiceField(
        choices=["mobile_money", "cash_on_delivery", "bank_transfer"]
    )
    delivery_address = serializers.CharField(max_length=255)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    item = OrderItemCreateSerializer()
    # is_group_order = serializers.BooleanField(required=False, default=False)


class OrderResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "total_amount", "payment_method", "status", "created_at"]
