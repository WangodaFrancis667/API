import hashlib
import hmac
import logging
from django.conf import settings

logger = logging.getLogger("payments")


def verify_webhook(headers: dict, raw_body: bytes) -> bool:
    """
    Verify webhook signature using HMAC-SHA256.
    Eversend typically sends signatures in the format: sha256=<signature>
    """
    secret = getattr(settings, "EVERSEND_WEBHOOK_SECRET", "")
    if not secret:
        logger.warning(
            "EVERSEND_WEBHOOK_SECRET not configured, skipping signature verification"
        )
        return True

    # Common signature header names
    signature_header = (
        headers.get("x-eversend-signature")
        or headers.get("x-hub-signature-256")
        or headers.get("signature")
        or ""
    )

    if not signature_header:
        logger.error("No signature header found in webhook request")
        return False

    try:
        # Remove 'sha256=' prefix if present
        if signature_header.startswith("sha256="):
            signature = signature_header[7:]
        else:
            signature = signature_header

        # Compute expected signature
        expected_signature = hmac.new(
            secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()

        # Compare signatures securely
        is_valid = hmac.compare_digest(signature, expected_signature)

        if not is_valid:
            logger.error(
                f"Webhook signature verification failed. Expected: {expected_signature}, Got: {signature}"
            )

        return is_valid

    except Exception as e:
        logger.exception(f"Error verifying webhook signature: {e}")
        return False


def validate_eversend_payload(payload: dict) -> tuple[bool, str]:
    """
    Validate the basic structure of Eversend webhook payload
    """
    required_fields = ["eventType", "transactionRef"]

    for field in required_fields:
        if not payload.get(field):
            return False, f"Missing required field: {field}"

    # Validate event type format
    event_type = payload.get("eventType", "").lower()
    valid_events = [
        "wallet.load.successful",
        "wallet.load.failed",
        "transaction.payout.successful",
        "transaction.payout.failed",
        "transaction.payout.pending",
    ]

    if not any(event in event_type for event in ["wallet.load", "transaction.payout"]):
        return False, f"Invalid eventType: {event_type}"

    # Validate transaction reference format
    transaction_ref = payload.get("transactionRef", "")
    if len(transaction_ref) < 5 or len(transaction_ref) > 128:
        return False, "Invalid transactionRef length"

    return True, ""
