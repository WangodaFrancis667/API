from django.db import models

class Transaction(models.Model):
    # Mirrors PHP: transactions table
    uuid = models.CharField(max_length=64, db_index=True)  # user identifier; keep CharField to match PHP
    transaction_ref = models.CharField(max_length=128, unique=True)
    transaction_id = models.CharField(max_length=128, null=True, blank=True)
    currency = models.CharField(max_length=8)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    service_fee = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=32, default="pending")  # pending/successful/failed/etc.
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_ref} ({self.status})"


class Wallet(models.Model):
    uuid = models.CharField(max_length=64, db_index=True)
    currency = models.CharField(max_length=8)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        unique_together = ("uuid", "currency")


class Commission(models.Model):
    currency = models.CharField(max_length=8, unique=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)


class Payment(models.Model):
    # Cleaned up from PHP insertPayments (which mixed variables)
    user_uuid = models.CharField(max_length=64, db_index=True)
    order_id = models.CharField(max_length=128, null=True, blank=True)
    transaction_ref = models.CharField(max_length=128, db_index=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    payment_method = models.CharField(max_length=64)   # e.g., "eversend"
    status = models.CharField(max_length=32, default="completed")
    created_at = models.DateTimeField(auto_now_add=True)


class AuditLog(models.Model):
    uuid = models.CharField(max_length=64, db_index=True)
    action = models.TextField()
    user_agent = models.CharField(max_length=512, default="Unknown")
    ip_address = models.CharField(max_length=64, default="Unknown")
    created_at = models.DateTimeField(auto_now_add=True)
