import logging
from decimal import Decimal
from django.db import transaction
from .models import Wallet, Commission, Payment, AuditLog

logger = logging.getLogger("payments")

def log_transaction(message: str, level: str = "info"):
    getattr(logger, level, logger.info)(message)

def update_wallet_amount(*, uuid: str, currency: str, amount: Decimal, is_add: bool = True) -> bool:
    """
    Credit or debit a wallet. Creates wallet if not exists (optional).
    """
    try:
        delta = abs(Decimal(amount))
        if not is_add:
            delta = -delta

        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            uuid=uuid, currency=currency, defaults={"amount": Decimal("0")}
        )
        wallet.amount = wallet.amount + delta
        wallet.save(update_fields=["amount"])

        log_transaction(
            f"Wallet {'credited' if is_add else 'debited'} for UUID={uuid}, Amount={delta}, Currency={currency}"
        )
        return True
    except Exception as e:
        log_transaction(f"Error updating wallet: {e}", "error")
        return False

def insert_payment(
    *, user_uuid: str, order_id: str | None, transaction_ref: str, amount: Decimal,
    payment_method: str, status: str = "completed"
) -> bool:
    try:
        Payment.objects.create(
            user_uuid=user_uuid,
            order_id=order_id,
            transaction_ref=transaction_ref,
            amount=Decimal(amount),
            payment_method=payment_method,
            status=status,
        )
        log_transaction(
            f"Payment recorded UUID={user_uuid}, Amount={amount}, TxRef={transaction_ref}, Method={payment_method}, Status={status}"
        )
        return True
    except Exception as e:
        log_transaction(f"Error inserting payment: {e}", "error")
        return False

def update_commission(*, currency: str, service_fee: Decimal, is_add: bool = True) -> bool:
    try:
        delta = abs(Decimal(service_fee))
        if not is_add:
            delta = -delta
        com, _ = Commission.objects.select_for_update().get_or_create(
            currency=currency, defaults={"amount": Decimal("0")}
        )
        com.amount = com.amount + delta
        com.save(update_fields=["amount"])
        log_transaction(f"Commission updated: Currency={currency}, Delta={delta}")
        return True
    except Exception as e:
        log_transaction(f"Error updating commission: {e}", "error")
        return False

def insert_audit_log(*, uuid: str, action: str, user_agent: str, ip_address: str) -> bool:
    try:
        AuditLog.objects.create(
            uuid=uuid,
            action=action,
            user_agent=user_agent or "Unknown",
            ip_address=ip_address or "Unknown",
        )
        log_transaction(f"Audit log inserted UUID={uuid}, Action={action}")
        return True
    except Exception as e:
        log_transaction(f"Error inserting audit log: {e}", "error")
        return False
