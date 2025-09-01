# payments/collections/views.py
import uuid
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from eversend_payments.utils import log_transaction
from eversend_payments.models import Transaction, AuditLog
from .serializers import FeeRequestSerializer, OTPRequestSerializer, MoMoRequestSerializer
from .services import get_collection_fees, request_otp, initiate_momo_transaction


class CollectionFeeView(APIView):
    """Handles calculation of collection fees"""

    def post(self, request):
        serializer = FeeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            response_data = get_collection_fees(**data)

            # Example: custom service fee logic
            deposit_commission = 0  # can be dynamic
            service_fee = round(data["amount"] * deposit_commission + 0.5)

            response_data["data"]["service_fee"] = service_fee
            response_data["data"]["charges"] += service_fee
            response_data["data"]["total_to_pay"] += service_fee
            response_data["data"]["payable_amount"] = service_fee + response_data["data"]["amount"]

            return Response(response_data)
        except Exception as e:
            return Response(
                {"status": "error", "message": "Deposit failed", "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CollectionOTPView(APIView):
    """Handles requesting OTP for mobile money"""

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]

        try:
            response_data = request_otp(phone)
            return Response(response_data)
        except Exception as e:
            return Response(
                {"status": "error", "message": "OTP request failed", "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CollectionMoMoView(APIView):
    """Handles initiating a MoMo collection"""

    def post(self, request):
        serializer = MoMoRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        transaction_ref = f"txn_{uuid.uuid4().hex[:12]}"

        try:
            with transaction.atomic():
                # Save transaction in DB
                txn = Transaction.objects.create(
                    uuid=data["uuid"],
                    currency=data["currency"],
                    transaction_ref=transaction_ref,
                    transaction_type="deposit",
                    account_number=data["phone"],
                    amount=data["amount"] - data["service_fee"],
                    country=data["country"],
                    service_fee=data["service_fee"],
                    charges=data["charges"],
                    status="pending",
                )

                # Audit log
                AuditLog.objects.create(
                    uuid=data["uuid"],
                    action="User Deposit Transaction",
                    user_agent=request.META.get("HTTP_USER_AGENT", "Unknown"),
                    ip_address=request.META.get("REMOTE_ADDR", "Unknown"),
                )

            # Call Eversend API
            payload = {
                "phone": data["phone"],
                "amount": data["amount"],
                "country": data["country"],
                "currency": data["currency"],
                "transactionRef": transaction_ref,
                "otp": data["otp"],
                "customer": data["customer"],
            }
            response_data = initiate_momo_transaction(payload)

            txn.status = "successful"
            txn.save(update_fields=["status"])

            return Response(response_data)

        except Exception as e:
            log_transaction(f"MoMo transaction failed: {e}", "error")
            Transaction.objects.filter(transaction_ref=transaction_ref).update(status="failed")
            return Response(
                {"status": "error", "message": "MoMo transaction failed", "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
