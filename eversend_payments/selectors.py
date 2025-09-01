from typing import Optional
from .models import Transaction

def get_transaction_by_ref(transaction_ref: str) -> Optional[Transaction]:
    try:
        return Transaction.objects.get(transaction_ref=transaction_ref)
    except Transaction.DoesNotExist:
        return None
