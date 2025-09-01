from rest_framework import serializers
from django.contrib.auth import get_user_model

from orders.models import Order

User = get_user_model()


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "total_amount", "payment_method", "status", "created_at"]


class VendorBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["wallet"]
