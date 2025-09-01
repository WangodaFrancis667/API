from django.db import models
from django.conf import settings
from decimal import Decimal


class VendorEarnings(models.Model):
    """
    Track vendor earnings from completed orders
    """
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="earnings",
        limit_choices_to={'role': 'vendor'}
    )
    order = models.OneToOneField(
        'orders.Order', 
        on_delete=models.PROTECT, 
        related_name="earnings"
    )
    
    # Financial details
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)  # Order total
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.10'))  # 10% default
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    net_earnings = models.DecimalField(max_digits=12, decimal_places=2)  # Amount vendor receives
    
    # Status tracking
    STATUS_PENDING = "pending"
    STATUS_PROCESSED = "processed"
    STATUS_PAID = "paid"
    
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSED, "Processed"),
        (STATUS_PAID, "Paid"),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['vendor', 'created_at']),
            models.Index(fields=['status']),
        ]
        
    def __str__(self):
        return f"Earnings for {self.vendor.username} - Order #{self.order.id}"
    
    def calculate_commission(self):
        """Calculate commission based on gross amount and rate"""
        self.commission_amount = self.gross_amount * (self.commission_rate / 100)
        self.net_earnings = self.gross_amount - self.commission_amount
        
    def save(self, *args, **kwargs):
        if not self.commission_amount or not self.net_earnings:
            self.calculate_commission()
        super().save(*args, **kwargs)


class VendorPayout(models.Model):
    """
    Track payouts made to vendors
    """
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="payouts",
        limit_choices_to={'role': 'vendor'}
    )
    
    # Financial details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Payout method
    PAYOUT_BANK = "bank_transfer"
    PAYOUT_MOBILE = "mobile_money"
    PAYOUT_WALLET = "wallet"
    
    PAYOUT_CHOICES = [
        (PAYOUT_BANK, "Bank Transfer"),
        (PAYOUT_MOBILE, "Mobile Money"),
        (PAYOUT_WALLET, "Wallet Credit"),
    ]
    
    payout_method = models.CharField(max_length=20, choices=PAYOUT_CHOICES)
    
    # Status
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    
    # Additional info
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['vendor', 'created_at']),
            models.Index(fields=['status']),
        ]
        
    def __str__(self):
        return f"Payout to {self.vendor.username} - ${self.amount}"


class VendorEarningSummary(models.Model):
    """
    Monthly summary of vendor earnings for quick reporting
    """
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="earning_summaries",
        limit_choices_to={'role': 'vendor'}
    )
    
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    
    # Summary data
    total_orders = models.PositiveIntegerField(default=0)
    gross_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_commission = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    net_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['vendor', 'year', 'month']
        indexes = [
            models.Index(fields=['vendor', 'year', 'month']),
        ]
        
    def __str__(self):
        return f"{self.vendor.username} - {self.year}/{self.month:02d}"
