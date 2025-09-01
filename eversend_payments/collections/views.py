# payments/collections/views.py
import uuid
from decimal import Decimal
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import UserRateThrottle

from eversend_payments.utils import log_transaction, get_client_ip
from eversend_payments.models import Transaction, AuditLog
from .serializers import (
    FeeRequestSerializer,
    OTPRequestSerializer,
    MoMoRequestSerializer,
)
from .services import get_collection_fees, request_otp, initiate_momo_transaction


class CollectionThrottle(UserRateThrottle):
    rate = "100/hour"


class CollectionFeeView(APIView):
    """Handles calculation of collection fees with enhanced validation"""

    throttle_classes = [CollectionThrottle]

    def post(self, request):
        client_ip = get_client_ip(request)

        try:
            serializer = FeeRequestSerializer(data=request.data)
            if not serializer.is_valid():
                log_transaction(
                    f"Invalid fee request from {client_ip}: {serializer.errors}",
                    "warning",
                )
                return Response(
                    {
                        "status": "error",
                        "message": "Invalid input",
                        "errors": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            data = serializer.validated_data
            log_transaction(
                f"Fee request from {client_ip}: {data['method']}-{data['currency']}-{data['amount']}"
            )

            response_data = get_collection_fees(**data)

            # Calculate service fee (customizable business logic)
            deposit_commission = 0.005  # 0.5% commission
            service_fee = round(float(data["amount"]) * deposit_commission, 2)

            # Enhance response with custom fees
            if "data" in response_data:
                response_data["data"]["service_fee"] = service_fee
                response_data["data"]["charges"] = (
                    response_data["data"].get("charges", 0) + service_fee
                )
                response_data["data"]["total_to_pay"] = (
                    response_data["data"].get("amount", 0) + service_fee
                )
                response_data["data"]["payable_amount"] = response_data["data"][
                    "total_to_pay"
                ]

            log_transaction(f"Fee calculation successful for {client_ip}")
            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as e:
            log_transaction(
                f"Validation error in fee request from {client_ip}: {e}", "error"
            )
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            log_transaction(
                f"Unexpected error in fee request from {client_ip}: {e}", "error"
            )
            return Response(
                {"status": "error", "message": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CollectionOTPView(APIView):
    """Handles requesting OTP for mobile money with rate limiting"""

    throttle_classes = [CollectionThrottle]

    def post(self, request):
        client_ip = get_client_ip(request)

        try:
            serializer = OTPRequestSerializer(data=request.data)
            if not serializer.is_valid():
                log_transaction(
                    f"Invalid OTP request from {client_ip}: {serializer.errors}",
                    "warning",
                )
                return Response(
                    {
                        "status": "error",
                        "message": "Invalid input",
                        "errors": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            phone = serializer.validated_data["phone"]
            masked_phone = f"{phone[:5]}***{phone[-2:]}" if len(phone) > 7 else "***"

            log_transaction(f"OTP request from {client_ip} for phone: {masked_phone}")

            response_data = request_otp(phone)

            log_transaction(f"OTP request successful for {masked_phone}")
            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as e:
            log_transaction(
                f"Validation error in OTP request from {client_ip}: {e}", "error"
            )
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            log_transaction(
                f"Unexpected error in OTP request from {client_ip}: {e}", "error"
            )
            return Response(
                {"status": "error", "message": "OTP request failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CollectionMoMoView(APIView):
    """Handles initiating a MoMo collection with comprehensive validation"""

    throttle_classes = [CollectionThrottle]

    def post(self, request):
        client_ip = get_client_ip(request)
        transaction_ref = f"txn_{uuid.uuid4().hex[:12]}"

        try:
            serializer = MoMoRequestSerializer(data=request.data)
            if not serializer.is_valid():
                log_transaction(
                    f"Invalid MoMo request from {client_ip}: {serializer.errors}",
                    "warning",
                )
                return Response(
                    {
                        "status": "error",
                        "message": "Invalid input",
                        "errors": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            data = serializer.validated_data
            log_transaction(
                f"MoMo transaction initiated from {client_ip}: {transaction_ref}"
            )

            with transaction.atomic():
                # Create transaction record
                txn = Transaction.objects.create(
                    uuid=data["uuid"],
                    currency=data["currency"],
                    transaction_ref=transaction_ref,
                    transaction_type="deposit",
                    account_number=data["phone"],
                    amount=Decimal(str(data["amount"]))
                    - Decimal(str(data["service_fee"])),
                    country=data["country"],
                    service_fee=Decimal(str(data["service_fee"])),
                    charges=Decimal(str(data["charges"])),
                    status="pending",
                )

                # Create audit log
                AuditLog.objects.create(
                    uuid=data["uuid"],
                    action=f"MoMo deposit initiated: {transaction_ref}",
                    user_agent=request.META.get("HTTP_USER_AGENT", "Unknown"),
                    ip_address=client_ip,
                )

                # Prepare payload for Eversend API
                api_payload = {
                    "phone": data["phone"],
                    "amount": data["amount"],
                    "country": data["country"],
                    "currency": data["currency"],
                    "transactionRef": transaction_ref,
                    "otp": data["otp"],
                    "customer": data["customer"],
                }

                # Call Eversend API
                response_data = initiate_momo_transaction(api_payload)

                # Update transaction status on successful API call
                txn.status = "processing"
                txn.save(update_fields=["status", "updated_at"])

                log_transaction(
                    f"MoMo transaction processed successfully: {transaction_ref}"
                )

                # Add transaction reference to response
                response_data["transactionRef"] = transaction_ref
                return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as e:
            log_transaction(
                f"Validation error in MoMo transaction from {client_ip}: {e}", "error"
            )
            # Update transaction status to failed if it was created
            Transaction.objects.filter(transaction_ref=transaction_ref).update(
                status="failed"
            )
            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "transactionRef": transaction_ref,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            log_transaction(
                f"Unexpected error in MoMo transaction from {client_ip}: {e}", "error"
            )
            # Update transaction status to failed if it was created
            Transaction.objects.filter(transaction_ref=transaction_ref).update(
                status="failed"
            )
            return Response(
                {
                    "status": "error",
                    "message": "MoMo transaction failed",
                    "transactionRef": transaction_ref,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
