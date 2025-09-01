from django.db import models
from django.conf import settings


# Group order model
# class GroupOrder(models.Model):
#     STATUS_OPEN = "open"
#     STATUS_CLOSED = "closed"
#     STATUS_FULFILLED = "fulfilled"
#     STATUS_CHOICES = [(STATUS_OPEN, "open"), (STATUS_CLOSED, "closed"), (STATUS_FULFILLED, "fulfilled")]

#     group_id = models.CharField(max_length=50, unique=True)
#     product_id = models.PositiveIntegerField(db_index=True)
#     total_quantity = models.PositiveBigIntegerField(default=0)
#     deadline = models.DateTimeField()

#     status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_OPEN)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         indexes = [
#             models.Index(fields=["product_id", "status"]),
#             models.Index(fields=["group_id"]),
#         ]

#     def __str__(self):
#         return f"{self.group_id} ({self.product_id})"


# Order model
class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_COMPLETED = "completed"  # Add completed status
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "pending"),
        (STATUS_PROCESSING, "processing"),
        (STATUS_SHIPPED, "shipped"),
        (STATUS_DELIVERED, "delivered"),
        (STATUS_COMPLETED, "completed"),  # Add completed status
        (STATUS_CANCELLED, "cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="vendor_orders",
        limit_choices_to={'role': 'vendor'}
    )
    # group_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    payment_method = models.CharField(max_length=50)
    delivery_address = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    return_eligible_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["vendor"]),
            # models.Index(fields=["group_id"]),
        ]

    def __str__(self):
        return f"Order #{self.pk}"


# Order item model
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_id = models.PositiveIntegerField(db_index=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=["order", "product_id"]),
        ]


# Order return model
class OrderReturn(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (s, s)
        for s in (STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_COMPLETED)
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="returns")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    return_reason = models.TextField()
    return_status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["order", "user"]),
            models.Index(fields=["return_status"]),
        ]
