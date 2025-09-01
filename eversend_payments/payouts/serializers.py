from rest_framework import serializers


class PayoutRequestSerializer(serializers.Serializer):
    token = serializers.CharField(
        help_text="Authentication token for the payout"
    )
    uuid = serializers.CharField(
        max_length=64,
        help_text="User unique identifier"
    )
    phoneNumber = serializers.CharField(
        max_length=20,
        help_text="Recipient's phone number"
    )
    firstName = serializers.CharField(
        max_length=50,
        help_text="Recipient's first name"
    )
    lastName = serializers.CharField(
        max_length=50,
        help_text="Recipient's last name"
    )
    country = serializers.CharField(
        max_length=3,
        help_text="Destination country code"
    )
    serviceFee = serializers.FloatField(
        min_value=0,
        help_text="Service fee for the payout"
    )
    totalAmount = serializers.FloatField(
        min_value=0.01,
        help_text="Total amount to be deducted from wallet"
    )

    def validate_phoneNumber(self, value):
        """Validate phone number format"""
        cleaned_phone = value.replace(" ", "").replace("-", "")
        if len(cleaned_phone) < 10:
            raise serializers.ValidationError("Invalid phone number")
        return cleaned_phone

    def validate_firstName(self, value):
        """Validate first name"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("First name must be at least 2 characters")
        if not value.replace(" ", "").replace("-", "").replace("'", "").isalpha():
            raise serializers.ValidationError("First name contains invalid characters")
        return value.strip().title()

    def validate_lastName(self, value):
        """Validate last name"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Last name must be at least 2 characters")
        if not value.replace(" ", "").replace("-", "").replace("'", "").isalpha():
            raise serializers.ValidationError("Last name contains invalid characters")
        return value.strip().title()

    def validate_country(self, value):
        """Validate country code"""
        if not value.isalpha() or len(value) != 2:
            raise serializers.ValidationError("Country must be a 2-letter country code")
        return value.upper()

    def validate(self, attrs):
        """Cross-field validation"""
        service_fee = attrs.get('serviceFee', 0)
        total_amount = attrs.get('totalAmount', 0)

        if service_fee > total_amount:
            raise serializers.ValidationError(
                "Service fee cannot exceed total amount"
            )

        return attrs


class PayoutQuotationSerializer(serializers.Serializer):
    sourceWallet = serializers.CharField(
        max_length=3,
        help_text="Source wallet currency"
    )
    amount = serializers.FloatField(
        min_value=0.01,
        help_text="Amount to convert"
    )
    type = serializers.CharField(
        max_length=20,
        help_text="Payout type (e.g., 'momo', 'bank')"
    )
    destinationCountry = serializers.CharField(
        max_length=3,
        help_text="Destination country code"
    )
    destinationCurrency = serializers.CharField(
        max_length=3,
        help_text="Destination currency code"
    )
    amountType = serializers.CharField(
        max_length=20,
        help_text="Amount type (e.g., 'source', 'destination')"
    )
    uuid = serializers.CharField(
        max_length=64,
        help_text="User unique identifier"
    )

    def validate_sourceWallet(self, value):
        """Validate source wallet currency"""
        if not value.isalpha() or len(value) != 3:
            raise serializers.ValidationError("Source wallet must be a 3-letter currency code")
        return value.upper()

    def validate_destinationCurrency(self, value):
        """Validate destination currency"""
        if not value.isalpha() or len(value) != 3:
            raise serializers.ValidationError("Destination currency must be a 3-letter currency code")
        return value.upper()

    def validate_destinationCountry(self, value):
        """Validate destination country"""
        if not value.isalpha() or len(value) != 2:
            raise serializers.ValidationError("Destination country must be a 2-letter country code")
        return value.upper()

    def validate_type(self, value):
        """Validate payout type"""
        allowed_types = ['momo', 'bank', 'card']
        if value.lower() not in allowed_types:
            raise serializers.ValidationError(f"Type must be one of: {allowed_types}")
        return value.lower()

    def validate_amountType(self, value):
        """Validate amount type"""
        allowed_types = ['source', 'destination']
        if value.lower() not in allowed_types:
            raise serializers.ValidationError(f"Amount type must be one of: {allowed_types}")
        return value.lower()
