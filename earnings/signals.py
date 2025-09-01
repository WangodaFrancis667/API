from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from orders.models import Order
from .models import VendorEarnings
from decimal import Decimal


@receiver(post_save, sender=Order)
def create_vendor_earnings(sender, instance, created, **kwargs):
    """
    Create vendor earnings record when order is completed
    """
    # Only create earnings for completed orders
    if instance.status == Order.STATUS_COMPLETED:
        # Check if earnings record already exists
        if not hasattr(instance, 'earnings'):
            # Get commission rate from vendor profile if available
            commission_rate = Decimal('10.00')  # Default 10%
            
            if hasattr(instance.vendor, 'vendor_profile'):
                commission_rate = instance.vendor.vendor_profile.commission_rate
            
            # Create earnings record
            VendorEarnings.objects.create(
                vendor=instance.vendor,
                order=instance,
                gross_amount=instance.total_amount,
                commission_rate=commission_rate
            )


@receiver(pre_save, sender=Order)
def handle_order_status_change(sender, instance, **kwargs):
    """
    Handle order status changes that might affect earnings
    """
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            
            # If order was cancelled, mark earnings as cancelled if they exist
            if (old_instance.status != Order.STATUS_CANCELLED and 
                instance.status == Order.STATUS_CANCELLED):
                
                if hasattr(instance, 'earnings'):
                    # You might want to handle cancellation logic here
                    pass
                    
        except Order.DoesNotExist:
            pass
