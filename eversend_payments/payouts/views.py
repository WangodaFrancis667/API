import uuid
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.http import JsonResponse
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import UserRateThrottle

from .serializers import PayoutRequestSerializer, PayoutQuotationSerializer
from .services import eversend_payout, eversend_payout_quotation
from eversend_payments.models import Transaction, Wallet, AuditLog, Commission, Earning
from eversend_payments.utils import log_transaction, get_client_ip


class PayoutThrottle(UserRateThrottle):
    rate = "50/hour"


class PayoutView(APIView):
    """Enhanced payout view with comprehensive validation and error handling"""

    throttle_classes = [PayoutThrottle]

    def post(self, request):
        client_ip = get_client_ip(request)
        transaction_ref = f"txn_{uuid.uuid4().hex[:12]}"

        try:
            serializer = PayoutRequestSerializer(data=request.data)
            if not serializer.is_valid():
                log_transaction(
                    f"Invalid payout request from {client_ip}: {serializer.errors}",
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
            log_transaction(f"Payout request from {client_ip}: {transaction_ref}")

            # Validate user has sufficient balance before calling API
            try:
                total_amount = Decimal(str(data["totalAmount"]))
            except (InvalidOperation, ValueError):
                return Response(
                    {"status": "error", "message": "Invalid total amount"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Call Eversend API first to validate the payout
            response_data = eversend_payout(
                token=data["token"],
                country=data["country"],
                phone=data["phoneNumber"],
                first_name=data["firstName"],
                last_name=data["lastName"],
                transaction_ref=transaction_ref,
            )

            # Extract transaction details from API response
            if (
                "data" not in response_data
                or "transaction" not in response_data["data"]
            ):
                log_transaction(
                    f"Invalid API response structure for payout {transaction_ref}",
                    "error",
                )
                return Response(
                    {"status": "error", "message": "Invalid API response"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            trx = response_data["data"]["transaction"]

            try:
                api_amount = Decimal(str(trx["amount"]))
                service_fee = Decimal(str(data["serviceFee"]))
                api_fees = Decimal(str(trx.get("fees", 0)))
            except (InvalidOperation, ValueError, KeyError):
                return Response(
                    {"status": "error", "message": "Invalid amount data from API"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            with transaction.atomic():
                # Check wallet balance
                try:
                    wallet = Wallet.objects.select_for_update().get(
                        uuid=data["uuid"], currency=trx["currency"]
                    )
                except Wallet.DoesNotExist:
                    return Response(
                        {"status": "error", "message": "Wallet not found"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if wallet.amount < total_amount:
                    log_transaction(
                        f"Insufficient balance for payout {transaction_ref}: {wallet.amount} < {total_amount}",
                        "warning",
                    )
                    return Response(
                        {"status": "error", "message": "Insufficient balance"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Create transaction record
                Transaction.objects.create(
                    uuid=data["uuid"],
                    currency=trx["currency"],
                    transaction_ref=transaction_ref,
                    transaction_type="withdraw",
                    account_number=data["phoneNumber"],
                    amount=api_amount,
                    country=trx.get("destinationCountry", data["country"]),
                    service_fee=service_fee,
                    charges=api_fees,
                    status="pending",
                )

                # Create audit log
                AuditLog.objects.create(
                    uuid=data["uuid"],
                    action=f"Payout initiated: {transaction_ref}",
                    user_agent=request.META.get("HTTP_USER_AGENT", "Unknown"),
                    ip_address=client_ip,
                )

                # Deduct from wallet
                wallet.amount -= total_amount
                wallet.save(update_fields=["amount", "updated_at"])

                # Create earning record
                Earning.objects.create(
                    uuid=data["uuid"],
                    currency=trx["currency"],
                    transaction_ref=transaction_ref,
                    service_name="exchange",
                    status="pending",
                    amount=service_fee,
                )

                # Update commission
                commission, _ = Commission.objects.select_for_update().get_or_create(
                    currency=trx["currency"], defaults={"amount": Decimal("0")}
                )
                commission.amount = models.F("amount") + service_fee
                commission.save(update_fields=["amount", "updated_at"])

            log_transaction(f"Payout processed successfully: {transaction_ref}")
            response_data["transactionRef"] = transaction_ref
            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as e:
            log_transaction(
                f"Validation error in payout from {client_ip}: {e}", "error"
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
                f"Unexpected error in payout from {client_ip}: {e}", "error"
            )
            # Update transaction status to failed if it was created
            Transaction.objects.filter(transaction_ref=transaction_ref).update(
                status="failed"
            )
            return Response(
                {
                    "status": "error",
                    "message": "Payout failed",
                    "transactionRef": transaction_ref,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PayoutQuotationView(APIView):
    """Enhanced payout quotation view with validation"""

    throttle_classes = [PayoutThrottle]

    def post(self, request):
        client_ip = get_client_ip(request)

        try:
            serializer = PayoutQuotationSerializer(data=request.data)
            if not serializer.is_valid():
                log_transaction(
                    f"Invalid quotation request from {client_ip}: {serializer.errors}",
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
                f"Payout quotation request from {client_ip}: {data['sourceWallet']} -> {data['destinationCurrency']}"
            )

            response_data = eversend_payout_quotation(
                source_wallet=data["sourceWallet"],
                amount=data["amount"],
                payout_type=data["type"],
                destination_country=data["destinationCountry"],
                destination_currency=data["destinationCurrency"],
                amount_type=data["amountType"],
            )

            log_transaction(f"Payout quotation successful for {client_ip}")
            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as e:
            log_transaction(
                f"Validation error in quotation from {client_ip}: {e}", "error"
            )
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            log_transaction(
                f"Unexpected error in quotation from {client_ip}: {e}", "error"
            )
            return Response(
                {"status": "error", "message": "Quotation request failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

            resp_data = response.json()
            quotation = resp_data["data"]["quotation"]

            withdraw_fee = 0.02  # Example: fetch from settings or DB
            service_fee = round(data["amount"] * withdraw_fee, 2)
            total_fees = quotation["totalFees"] + service_fee
            final_total = data["amount"] + total_fees

            # Check wallet balance
            wallet = Wallet.objects.filter(
                uuid=data["uuid"], currency=data["sourceWallet"]
            ).first()
            if not wallet or wallet.amount < final_total:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Insufficient wallet balance",
                        "rate": quotation["exchangeRate"],
                        "totalAmountRequired": final_total,
                        "service_fee": service_fee,
                        "total_fees": total_fees,
                    },
                    status=400,
                )

            quotation.update(
                {
                    "service_fee": service_fee,
                    "total_fees": total_fees,
                    "totalAmountRequired": final_total,
                }
            )
            resp_data["data"]["quotation"] = quotation

            return JsonResponse(resp_data, status=200)

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
