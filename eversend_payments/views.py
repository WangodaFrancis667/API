from decimal import Decimal
import json
import logging

from django.db import transaction as db_transaction
from django.http import HttpRequest
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import Transaction
from .selectors import get_transaction_by_ref
from .services.eversend import get_eversend_token
from .utils import (
    log_transaction,
    update_wallet_amount,
    insert_payment,
    update_commission,
    insert_audit_log,
)
from .validators import verify_webhook

logger = logging.getLogger("payments")


class EversendTokenView(APIView):
    """
    Replacement for:
        $tokenData = getEversendToken();
        echo "Access Token: " . $tokenData['token'] ...
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request: HttpRequest):
        token = get_eversend_token()
        if token:
            return Response({"token": token}, status=status.HTTP_200_OK)
        return Response({"detail": "Failed to retrieve token"}, status=status.HTTP_502_BAD_GATEWAY)


class EversendWebhookView(APIView):
    """
    Replacement for webhook PHP script with DB transaction & logging.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request: HttpRequest):
        raw_body = request.body
        headers = {k.lower(): v for k, v in request.headers.items()}

        # Optional signature verification hook
        if not verify_webhook(headers, raw_body):
            log_transaction("Webhook signature verification failed", "error")
            return Response({"detail": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = request.data if isinstance(request.data, dict) else json.loads(raw_body.decode("utf-8"))
        except Exception:
            log_transaction("Invalid JSON payload", "error")
            return Response({"detail": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)

        event_type = (payload.get("eventType") or "").lower()
        status_str = (payload.get("status") or "unknown").lower()
        transaction_id = payload.get("transactionId")
        transaction_ref = payload.get("transactionRef")
        currency = payload.get("currency")
        amount = payload.get("amount") or 0

        is_wallet_load = "wallet.load" in event_type
        is_payout = "transaction.payout" in event_type

        log_transaction(
            f"Webhook Data: eventType={event_type}, status={status_str}, txId={transaction_id}, txRef={transaction_ref}, currency={currency}, amount={amount}; headers={headers}"
        )

        with db_transaction.atomic():
            # Update transaction row
            if transaction_ref:
                Transaction.objects.filter(transaction_ref=transaction_ref).update(
                    status=status_str, transaction_id=transaction_id
                )
            tx = get_transaction_by_ref(transaction_ref) if transaction_ref else None

            if not tx:
                log_transaction(f"No matching transaction found for ref: {transaction_ref}", "error")
                # Still return 200 to avoid retries storm; adjust if you prefer 404/400.
                return Response({"detail": "No matching transaction"}, status=status.HTTP_200_OK)

            # Use DB values as canonical
            uuid = tx.uuid
            currency = tx.currency or currency
            amount = Decimal(tx.amount or amount)
            service_fee = Decimal(tx.service_fee or 0)

            # Business rules mapped from PHP:
            # - Successful wallet.load => credit wallet, record payment, update commission (0 by default here)
            # - Failed payout => refund (credit) wallet, record payment (deposit-like), update commission reversal
            if is_wallet_load and status_str == "successful":
                update_wallet_amount(uuid=uuid, currency=currency, amount=amount, is_add=True)
                insert_payment(
                    user_uuid=uuid,
                    order_id=None,
                    transaction_ref=transaction_ref,
                    amount=amount,
                    payment_method="eversend",
                    status="completed",
                )
                update_commission(currency=currency, service_fee=service_fee, is_add=True)

            elif is_payout and status_str != "successful":
                # Reverse payout (credit back)
                update_wallet_amount(uuid=uuid, currency=currency, amount=amount, is_add=True)
                insert_payment(
                    user_uuid=uuid,
                    order_id=None,
                    transaction_ref=transaction_ref,
                    amount=amount,
                    payment_method="eversend",
                    status="reversed",
                )
                update_commission(currency=currency, service_fee=service_fee, is_add=False)

            # Audit log
            insert_audit_log(
                uuid=uuid,
                action=f"Transaction status updated: {status_str}",
                user_agent=request.META.get("HTTP_USER_AGENT", "Unknown"),
                ip_address=request.META.get("REMOTE_ADDR", "Unknown"),
            )

        return Response({"detail": "Success"}, status=status.HTTP_200_OK)
