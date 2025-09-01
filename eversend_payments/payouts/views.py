import uuid
from django.db import transaction
from django.http import JsonResponse
from rest_framework.views import APIView
from .serializers import PayoutRequestSerializer, PayoutQuotationSerializer
from .services import eversend_payout, eversend_payout_quotation
from eversend_payments.models import Transaction, Wallet, AuditLog, Commission, Earning


class PayoutView(APIView):
    def post(self, request):
        serializer = PayoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        transaction_ref = f"txn_{uuid.uuid4().hex[:12]}"

        try:
            # Call Eversend API
            response = eversend_payout(
                token=data["token"],
                country=data["country"],
                phone=data["phoneNumber"],
                first_name=data["firstName"],
                last_name=data["lastName"],
                transaction_ref=transaction_ref,
            )
            if response.status_code != 200:
                return JsonResponse(response.json(), status=response.status_code)

            resp_data = response.json()
            trx = resp_data["data"]["transaction"]

            with transaction.atomic():
                # Save transaction
                Transaction.objects.create(
                    uuid=data["uuid"],
                    currency=trx["currency"],
                    transaction_ref=transaction_ref,
                    transaction_type="withdraw",
                    account_number=data["phoneNumber"],
                    amount=trx["amount"],
                    country=trx["destinationCountry"],
                    service_fee=data["serviceFee"],
                    charges=trx["fees"],
                    status="pending",
                )

                # Audit log
                AuditLog.objects.create(
                    uuid=data["uuid"],
                    action="Card Withdraw Transaction",
                    user_agent=request.META.get("HTTP_USER_AGENT", "Unknown"),
                    ip_address=request.META.get("REMOTE_ADDR", "Unknown"),
                )

                # Deduct wallet
                wallet = Wallet.objects.select_for_update().get(uuid=data["uuid"], currency=trx["currency"])
                if wallet.amount < trx["amount"]:
                    return JsonResponse({"status": "error", "message": "Insufficient balance"}, status=400)
                wallet.amount -= trx["amount"]
                wallet.save()

                # Add earnings
                Earning.objects.create(
                    uuid=data["uuid"],
                    currency=trx["currency"],
                    transaction_ref=transaction_ref,
                    service_name="exchange",
                    status="completed",
                    amount=data["serviceFee"],
                )

                # Update commission
                Commission.objects.filter(wallet=trx["currency"]).update(amount=models.F("amount") + data["serviceFee"])

            return JsonResponse(resp_data, status=200)

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


class PayoutQuotationView(APIView):
    def post(self, request):
        serializer = PayoutQuotationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            response = eversend_payout_quotation(
                source_wallet=data["sourceWallet"],
                amount=data["amount"],
                payout_type=data["type"],
                destination_country=data["destinationCountry"],
                destination_currency=data["destinationCurrency"],
                amount_type=data["amountType"],
            )
            if response.status_code != 200:
                return JsonResponse(response.json(), status=response.status_code)

            resp_data = response.json()
            quotation = resp_data["data"]["quotation"]

            withdraw_fee = 0.02  # Example: fetch from settings or DB
            service_fee = round(data["amount"] * withdraw_fee, 2)
            total_fees = quotation["totalFees"] + service_fee
            final_total = data["amount"] + total_fees

            # Check wallet balance
            wallet = Wallet.objects.filter(uuid=data["uuid"], currency=data["sourceWallet"]).first()
            if not wallet or wallet.amount < final_total:
                return JsonResponse({
                    "status": "error",
                    "message": "Insufficient wallet balance",
                    "rate": quotation["exchangeRate"],
                    "totalAmountRequired": final_total,
                    "service_fee": service_fee,
                    "total_fees": total_fees,
                }, status=400)

            quotation.update({
                "service_fee": service_fee,
                "total_fees": total_fees,
                "totalAmountRequired": final_total,
            })
            resp_data["data"]["quotation"] = quotation

            return JsonResponse(resp_data, status=200)

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
