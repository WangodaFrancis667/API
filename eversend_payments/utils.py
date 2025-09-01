import logging
from decimal import Decimal
from typing import Optional
from django.db import transaction
from django.http import HttpRequest
from .models import Wallet, Commission, Payment, AuditLog

logger = logging.getLogger("payments")


def log_transaction(message: str, level: str = "info"):
    """Enhanced logging with structured format"""
    log_method = getattr(logger, level, logger.info)
    log_method(f"[EVERSEND_PAYMENTS] {message}")


def get_client_ip(request: HttpRequest) -> str:
    """Extract client IP address from request, considering proxy headers"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "Unknown")
    return ip


def validate_currency(currency: str) -> bool:
    """Validate currency format"""
    if not currency or len(currency) != 3:
        return False
    return currency.isalpha() and currency.isupper()


def validate_amount(amount) -> Optional[Decimal]:
    """Validate and convert amount to Decimal"""
    try:
        decimal_amount = Decimal(str(amount))
        if decimal_amount <= 0:
            return None
        if decimal_amount > Decimal("999999999.99"):  # Reasonable upper limit
            return None
        return decimal_amount
    except (ValueError, TypeError, OverflowError):
        return None


def update_wallet_amount(
    *, uuid: str, currency: str, amount: Decimal, is_add: bool = True
) -> bool:
    """
    Credit or debit a wallet with enhanced validation and error handling.
    Creates wallet if it doesn't exist.
    """
    if not uuid or not currency:
        log_transaction(
            "Invalid UUID or currency provided to update_wallet_amount", "error"
        )
        return False

    if not validate_currency(currency):
        log_transaction(f"Invalid currency format: {currency}", "error")
        return False

    validated_amount = validate_amount(amount)
    if validated_amount is None:
        log_transaction(f"Invalid amount: {amount}", "error")
        return False

    try:
        with transaction.atomic():
            delta = validated_amount if is_add else -validated_amount

            wallet, created = Wallet.objects.select_for_update().get_or_create(
                uuid=uuid, currency=currency, defaults={"amount": Decimal("0")}
            )

            new_amount = wallet.amount + delta

            # Prevent negative balances for debits
            if not is_add and new_amount < 0:
                log_transaction(
                    f"Insufficient balance for UUID={uuid}, Currency={currency}, "
                    f"Current={wallet.amount}, Requested={validated_amount}",
                    "error",
                )
                return False

            wallet.amount = new_amount
            wallet.save(update_fields=["amount", "updated_at"])

            action = "credited" if is_add else "debited"
            log_transaction(
                f"Wallet {action}: UUID={uuid}, Amount={delta}, Currency={currency}, "
                f"New Balance={new_amount}, Created={created}"
            )
            return True

    except Exception as e:
        log_transaction(f"Error updating wallet: {e}", "error")
        return False


def insert_payment(
    *,
    user_uuid: str,
    order_id: str | None,
    transaction_ref: str,
    amount: Decimal,
    payment_method: str,
    status: str = "completed",
) -> bool:
    """
    Insert payment record with validation
    """
    if not all([user_uuid, transaction_ref, payment_method]):
        log_transaction("Missing required fields for payment insertion", "error")
        return False

    validated_amount = validate_amount(amount)
    if validated_amount is None:
        log_transaction(f"Invalid payment amount: {amount}", "error")
        return False

    try:
        with transaction.atomic():
            payment = Payment.objects.create(
                user_uuid=user_uuid,
                order_id=order_id,
                transaction_ref=transaction_ref,
                amount=validated_amount,
                payment_method=payment_method,
                status=status,
            )

            log_transaction(
                f"Payment recorded: ID={payment.id}, UUID={user_uuid}, Amount={validated_amount}, "
                f"TxRef={transaction_ref}, Method={payment_method}, Status={status}"
            )
            return True

    except Exception as e:
        log_transaction(f"Error inserting payment: {e}", "error")
        return False


def update_commission(
    *, currency: str, service_fee: Decimal, is_add: bool = True
) -> bool:
    """
    Update commission with validation and error handling
    """
    if not validate_currency(currency):
        log_transaction(f"Invalid currency for commission: {currency}", "error")
        return False

    validated_fee = (
        validate_amount(abs(service_fee)) if service_fee != 0 else Decimal("0")
    )
    if validated_fee is None and service_fee != 0:
        log_transaction(f"Invalid service fee: {service_fee}", "error")
        return False

    try:
        with transaction.atomic():
            delta = validated_fee if is_add else -validated_fee

            commission, created = Commission.objects.select_for_update().get_or_create(
                currency=currency, defaults={"amount": Decimal("0")}
            )

            new_amount = commission.amount + delta

            # Prevent negative commission (shouldn't happen in normal flow)
            if new_amount < 0:
                log_transaction(
                    f"Commission would go negative: Currency={currency}, "
                    f"Current={commission.amount}, Delta={delta}",
                    "warning",
                )
                new_amount = Decimal("0")

            commission.amount = new_amount
            commission.save(update_fields=["amount", "updated_at"])

            log_transaction(
                f"Commission updated: Currency={currency}, Delta={delta}, "
                f"New Amount={new_amount}, Created={created}"
            )
            return True

    except Exception as e:
        log_transaction(f"Error updating commission: {e}", "error")
        return False


def insert_audit_log(
    *, uuid: str, action: str, user_agent: str, ip_address: str
) -> bool:
    """
    Insert audit log with validation
    """
    if not all([uuid, action]):
        log_transaction("Missing required fields for audit log", "error")
        return False

    # Truncate long values to prevent database errors
    action = action[:1000] if action else "Unknown action"
    user_agent = user_agent[:512] if user_agent else "Unknown"
    ip_address = ip_address[:64] if ip_address else "Unknown"

    try:
        audit_log = AuditLog.objects.create(
            uuid=uuid,
            action=action,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        log_transaction(f"Audit log created: ID={audit_log.id}, UUID={uuid}")
        return True

    except Exception as e:
        log_transaction(f"Error inserting audit log: {e}", "error")
        return False
