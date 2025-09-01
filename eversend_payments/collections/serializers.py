# payments/collections/serializers.py
from rest_framework import serializers
from decimal import Decimal


class FeeRequestSerializer(serializers.Serializer):
    method = serializers.CharField(
        max_length=50, help_text="Payment method (e.g., 'momo', 'bank')"
    )
    currency = serializers.CharField(
        max_length=3, help_text="3-letter currency code (e.g., 'USD', 'UGX')"
    )
    amount = serializers.FloatField(
        min_value=500, max_value=4000000, help_text="Amount to be collected"
    )

    def validate_currency(self, value):
        """Validate currency format"""
        if not value.isalpha() or len(value) != 3:
            raise serializers.ValidationError(
                "Currency must be a 3-letter alphabetic code"
            )
        return value.upper()

    def validate_method(self, value):
        """Validate payment method"""
        allowed_methods = ["momo", "bank", "card"]
        if value.lower() not in allowed_methods:
            raise serializers.ValidationError(
                f"Method must be one of: {allowed_methods}"
            )
        return value.lower()


class OTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(
        max_length=20, help_text="Phone number in international format"
    )

    def validate_phone(self, value):
        """Validate phone number format"""
        # Remove common separators
        cleaned_phone = (
            value.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        )

        # Basic validation
        if len(cleaned_phone) < 10:
            raise serializers.ValidationError("Phone number is too short")

        if not cleaned_phone.replace("+", "").isdigit():
            raise serializers.ValidationError(
                "Phone number contains invalid characters"
            )

        return cleaned_phone


class MoMoRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(
        max_length=20, help_text="Phone number for mobile money"
    )
    amount = serializers.FloatField(
        min_value=0.01, help_text="Total transaction amount"
    )
    country = serializers.CharField(
        max_length=3, help_text="2-letter country code (e.g., 'UG', 'KE')"
    )
    currency = serializers.CharField(max_length=3, help_text="3-letter currency code")
    otp = serializers.CharField(
        max_length=10, help_text="OTP code from mobile money provider"
    )
    customer = serializers.CharField(max_length=255, help_text="Customer identifier")
    uuid = serializers.CharField(max_length=50, help_text="User unique identifier")
    service_fee = serializers.FloatField(min_value=0, help_text="Service fee charged")
    charges = serializers.FloatField(min_value=0, help_text="Additional charges")

    def validate_currency(self, value):
        """Validate currency format"""
        if not value.isalpha() or len(value) != 3:
            raise serializers.ValidationError(
                "Currency must be a 3-letter alphabetic code"
            )
        return value.upper()

    def validate_country(self, value):
        """Validate country code"""
        if not value.isalpha() or len(value) != 2:
            raise serializers.ValidationError("Country must be a 2-letter country code")
        return value.upper()

    def validate_phone(self, value):
        """Validate phone number"""
        cleaned_phone = value.replace(" ", "").replace("-", "")
        if len(cleaned_phone) < 10:
            raise serializers.ValidationError("Invalid phone number")
        return cleaned_phone

    def validate_otp(self, value):
        """Validate OTP code"""
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only digits")
        if len(value) < 4 or len(value) > 10:
            raise serializers.ValidationError("OTP must be between 4 and 10 digits")
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        amount = attrs.get("amount", 0)
        service_fee = attrs.get("service_fee", 0)
        charges = attrs.get("charges", 0)

        if service_fee + charges > amount:
            raise serializers.ValidationError(
                "Service fee and charges cannot exceed the total amount"
            )

        # Ensure minimum net amount
        net_amount = amount - service_fee - charges
        if net_amount < 100:  # Minimum net amount
            raise serializers.ValidationError(
                "Net amount after fees must be at least 100"
            )

        return attrs
