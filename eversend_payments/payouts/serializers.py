from rest_framework import serializers


class PayoutRequestSerializer(serializers.Serializer):
    token = serializers.CharField()
    uuid = serializers.CharField()
    phoneNumber = serializers.CharField()
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    country = serializers.CharField()
    serviceFee = serializers.FloatField()
    totalAmount = serializers.FloatField()


class PayoutQuotationSerializer(serializers.Serializer):
    sourceWallet = serializers.CharField()
    amount = serializers.FloatField()
    type = serializers.CharField()
    destinationCountry = serializers.CharField()
    destinationCurrency = serializers.CharField()
    amountType = serializers.CharField()
    uuid = serializers.CharField()
