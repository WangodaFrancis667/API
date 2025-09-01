# payments/collections/serializers.py
from rest_framework import serializers


class FeeRequestSerializer(serializers.Serializer):
    method = serializers.CharField(max_length=50)
    currency = serializers.CharField(max_length=10)
    amount = serializers.FloatField(min_value=500, max_value=4000000)


class OTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)


class MoMoRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    amount = serializers.FloatField()
    country = serializers.CharField(max_length=10)
    currency = serializers.CharField(max_length=10)
    otp = serializers.CharField(max_length=10)
    customer = serializers.CharField(max_length=255)
    uuid = serializers.CharField(max_length=50)
    service_fee = serializers.FloatField()
    charges = serializers.FloatField()
