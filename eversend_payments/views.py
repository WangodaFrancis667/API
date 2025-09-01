from decimal import Decimal
import json
import logging

from django.db import transaction as db_transaction
from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle

from .models import Transaction
from .selectors import get_transaction_by_ref
from .services.eversend import get_eversend_token
from .utils import (
    log_transaction,
    update_wallet_amount,
    insert_payment,
    update_commission,
    insert_audit_log,
    get_client_ip,
)
from .validators import verify_webhook, validate_eversend_payload

logger = logging.getLogger("payments")


class EversendTokenView(APIView):
    """
    Secure endpoint for retrieving Eversend access token.
    This endpoint should be restricted to admin users only.
    """
    # Add authentication for production
    # authentication_classes = [TokenAuthentication, SessionAuthentication]
    # permission_classes = [IsAdminUser]
    
    # For now, keeping as unrestricted but should be secured
    authentication_classes = []
    permission_classes = []

    def get(self, request: HttpRequest):
        client_ip = get_client_ip(request)
        
        # Log the request for security monitoring
        log_transaction(f"Token request from IP: {client_ip}")
        
        try:
            token = get_eversend_token()
            if token:
                # Don't log the actual token for security
                log_transaction(f"Token successfully retrieved for IP: {client_ip}")
                
                # In production, you might want to return limited info
                # or require additional authentication
                return Response(
                    {"status": "success", "token": token}, 
                    status=status.HTTP_200_OK
                )
            else:
                log_transaction(f"Failed to retrieve token for IP: {client_ip}", "error")
                return Response(
                    {"detail": "Failed to retrieve token"}, 
                    status=status.HTTP_502_BAD_GATEWAY
                )
                
        except Exception as e:
            log_transaction(f"Unexpected error retrieving token for IP {client_ip}: {e}", "error")
            return Response(
                {"detail": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EversendWebhookThrottle(AnonRateThrottle):
    rate = '1000/hour'


@method_decorator(csrf_exempt, name='dispatch')
class EversendWebhookView(APIView):
    """
    Production-ready webhook handler for Eversend payments
    with proper security, validation, and error handling.
    """
    authentication_classes = []
    permission_classes = []
    throttle_classes = [EversendWebhookThrottle]

    def post(self, request: HttpRequest):
        raw_body = request.body
        headers = {k.lower(): v for k, v in request.headers.items()}
        client_ip = get_client_ip(request)
        
        # Log incoming webhook request
        log_transaction(f"Webhook received from IP: {client_ip}, Headers: {dict(headers)}")

        # Verify webhook signature
        if not verify_webhook(headers, raw_body):
            log_transaction(f"Webhook signature verification failed from IP: {client_ip}", "error")
            insert_audit_log(
                uuid="system",
                action=f"Failed webhook signature verification from IP: {client_ip}",
                user_agent=request.META.get("HTTP_USER_AGENT", "Unknown"),
                ip_address=client_ip,
            )
            return Response(
                {"detail": "Invalid signature"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Parse payload
        try:
            payload = request.data if isinstance(request.data, dict) else json.loads(raw_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            log_transaction(f"Invalid JSON payload from IP {client_ip}: {e}", "error")
            return Response(
                {"detail": "Invalid JSON payload"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate payload structure
        is_valid, validation_error = validate_eversend_payload(payload)
        if not is_valid:
            log_transaction(f"Invalid payload structure from IP {client_ip}: {validation_error}", "error")
            return Response(
                {"detail": f"Invalid payload: {validation_error}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract payload data
        event_type = payload.get("eventType", "").lower()
        status_str = payload.get("status", "unknown").lower()
        transaction_id = payload.get("transactionId")
        transaction_ref = payload.get("transactionRef")
        currency = payload.get("currency", "")
        amount = payload.get("amount", 0)

        is_wallet_load = "wallet.load" in event_type
        is_payout = "transaction.payout" in event_type

        log_transaction(
            f"Processing webhook: eventType={event_type}, status={status_str}, "
            f"txId={transaction_id}, txRef={transaction_ref}, "
            f"currency={currency}, amount={amount}, IP={client_ip}"
        )

        try:
            with db_transaction.atomic():
                # Find and update transaction
                if not transaction_ref:
                    log_transaction("Missing transaction reference in webhook", "error")
                    return Response(
                        {"detail": "Missing transaction reference"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Update transaction status
                updated_count = Transaction.objects.filter(
                    transaction_ref=transaction_ref
                ).update(
                    status=status_str, 
                    transaction_id=transaction_id
                )
                
                if updated_count == 0:
                    log_transaction(f"No transaction found for ref: {transaction_ref}", "warning")
                    # Return 200 to prevent webhook retries for non-existent transactions
                    return Response(
                        {"detail": "Transaction not found, but acknowledged"}, 
                        status=status.HTTP_200_OK
                    )

                # Get updated transaction
                tx = get_transaction_by_ref(transaction_ref)
                if not tx:
                    log_transaction(f"Failed to retrieve transaction after update: {transaction_ref}", "error")
                    return Response(
                        {"detail": "Internal error"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                # Use database values as canonical source
                uuid = tx.uuid
                currency = tx.currency or currency
                amount = Decimal(str(tx.amount or amount))
                service_fee = Decimal(str(tx.service_fee or 0))

                # Process business logic based on event type and status
                if is_wallet_load and status_str == "successful":
                    self._process_successful_wallet_load(
                        uuid, currency, amount, service_fee, transaction_ref
                    )
                elif is_payout and status_str != "successful":
                    self._process_failed_payout(
                        uuid, currency, amount, service_fee, transaction_ref
                    )

                # Create audit log
                insert_audit_log(
                    uuid=uuid,
                    action=f"Webhook processed: {event_type} - {status_str}",
                    user_agent=request.META.get("HTTP_USER_AGENT", "Unknown"),
                    ip_address=client_ip,
                )

            log_transaction(f"Successfully processed webhook for transaction: {transaction_ref}")
            return Response({"detail": "Webhook processed successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            log_transaction(f"Error processing webhook: {e}", "error")
            # Create system audit log for the error
            insert_audit_log(
                uuid="system",
                action=f"Webhook processing error: {str(e)[:200]}",
                user_agent=request.META.get("HTTP_USER_AGENT", "Unknown"),
                ip_address=client_ip,
            )
            return Response(
                {"detail": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_successful_wallet_load(self, uuid: str, currency: str, amount: Decimal, 
                                      service_fee: Decimal, transaction_ref: str):
        """Process successful wallet load transaction"""
        if not update_wallet_amount(uuid=uuid, currency=currency, amount=amount, is_add=True):
            raise Exception("Failed to update wallet amount")
            
        if not insert_payment(
            user_uuid=uuid,
            order_id=None,
            transaction_ref=transaction_ref,
            amount=amount,
            payment_method="eversend",
            status="completed",
        ):
            raise Exception("Failed to insert payment record")
            
        if not update_commission(currency=currency, service_fee=service_fee, is_add=True):
            raise Exception("Failed to update commission")

    def _process_failed_payout(self, uuid: str, currency: str, amount: Decimal, 
                             service_fee: Decimal, transaction_ref: str):
        """Process failed payout transaction (refund)"""
        if not update_wallet_amount(uuid=uuid, currency=currency, amount=amount, is_add=True):
            raise Exception("Failed to refund wallet amount")
            
        if not insert_payment(
            user_uuid=uuid,
            order_id=None,
            transaction_ref=transaction_ref,
            amount=amount,
            payment_method="eversend",
            status="reversed",
        ):
            raise Exception("Failed to insert refund payment record")
            
        if not update_commission(currency=currency, service_fee=service_fee, is_add=False):
            raise Exception("Failed to reverse commission")
