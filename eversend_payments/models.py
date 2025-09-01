from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdraw', 'Withdraw'),
        ('transfer', 'Transfer'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('reversed', 'Reversed'),
    ]

    # Core fields
    uuid = models.CharField(max_length=64, db_index=True)  # user identifier
    transaction_ref = models.CharField(max_length=128, unique=True)
    transaction_id = models.CharField(max_length=128, null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='deposit')
    
    # Financial fields
    currency = models.CharField(max_length=8)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    service_fee = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    charges = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    
    # Transaction details
    account_number = models.CharField(max_length=50, null=True, blank=True)
    country = models.CharField(max_length=10, null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uuid', 'status']),
            models.Index(fields=['transaction_ref']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.transaction_ref} ({self.status})"


class Wallet(models.Model):
    uuid = models.CharField(max_length=64, db_index=True)
    currency = models.CharField(max_length=8)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("uuid", "currency")
        indexes = [
            models.Index(fields=['uuid', 'currency']),
        ]

    def __str__(self):
        return f"{self.uuid} - {self.currency}: {self.amount}"


class Commission(models.Model):
    currency = models.CharField(max_length=8, unique=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.currency}: {self.amount}"


class Payment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
        ('cancelled', 'Cancelled'),
    ]

    # Core identifiers
    user_uuid = models.CharField(max_length=64, db_index=True)
    order_id = models.CharField(max_length=128, null=True, blank=True)
    transaction_ref = models.CharField(max_length=128, db_index=True)
    
    # Payment details
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    payment_method = models.CharField(max_length=64)   # e.g., "eversend"
    status = models.CharField(max_length=32, choices=PAYMENT_STATUS, default="completed")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_uuid']),
            models.Index(fields=['transaction_ref']),
        ]

    def __str__(self):
        return f"Payment {self.transaction_ref} - {self.amount}"


class Earning(models.Model):
    EARNING_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    uuid = models.CharField(max_length=64, db_index=True)
    currency = models.CharField(max_length=8)
    transaction_ref = models.CharField(max_length=128, db_index=True)
    service_name = models.CharField(max_length=100, default='exchange')
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, choices=EARNING_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['transaction_ref']),
        ]

    def __str__(self):
        return f"Earning {self.uuid} - {self.amount} {self.currency}"


class AuditLog(models.Model):
    uuid = models.CharField(max_length=64, db_index=True)
    action = models.TextField()
    user_agent = models.CharField(max_length=512, default="Unknown")
    ip_address = models.CharField(max_length=64, default="Unknown")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uuid', 'created_at']),
        ]

    def __str__(self):
        return f"Audit {self.uuid} - {self.action[:50]}"
