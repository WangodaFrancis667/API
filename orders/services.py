# business logic, atomic and locked

import uuid

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from django.db.models import F

from rest_framework import serializers

from .models import (
    GroupOrder, Order, OrderItem
)

from notifications.services import (
    notify_vendor_new_order, notify_buyer_status
)

# Import the Products model from productManagement app
from productManagement.models import Products

def get_product(product_id: int):
    """
    Return dict: {id, vendor_id, min_quantity, regular_price, group_price, title}
    Fetch product details from the Products model.
    """
    try:
        # Get the product, ensuring it's active
        product = Products.objects.select_related('vendor').get(
            id=product_id, 
            is_active=True
        )
        
        return {
            'id': product.id,
            'vendor_id': product.vendor.id,
            'min_quantity': product.min_quantity,
            'regular_price': product.regular_price,
            'group_price': product.group_price,
            'title': product.title
        }
    
    except Products.DoesNotExist:
        raise serializers.ValidationError("This product does not exist!")
        # Return None or raise a custom exception based on your error handling strategy
        # return None
        # Alternative: raise ValueError(f"Product with id {product_id} not found or inactive")

    

def _price_guard(calc_subtotal: Decimal, expected_subtotal: Decimal) -> None:
    if abs(calc_subtotal - expected_subtotal) > Decimal("0.01"):
        raise ValueError("Price mismatch with current product price")



# Creating an individual order
def create_individual_order(
    *, buyer_id: int, vendor_id: int, product_id: int, quantity: int,
    unit_price: Decimal, payment_method: str, delivery_address: str,
    subtotal: Decimal, delivery_fee: Decimal, total_amount: Decimal
):
    product = get_product(product_id)
    expected_subtotal = Decimal(product["regular_price"]) * quantity
    _price_guard(subtotal, expected_subtotal)

    with transaction.atomic():  # ensures all-or-nothing  
        order = Order.objects.create(
            user_id=buyer_id,
            vendor_id=vendor_id,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total_amount=total_amount,
            payment_method=payment_method,
            delivery_address=delivery_address,
            status=Order.STATUS_PENDING,
        )
        OrderItem.objects.create(
            order=order,
            product_id=product_id,
            quantity=quantity,
            unit_price=Decimal(product["regular_price"]),
            price=expected_subtotal,
        )

    # Side effects after commit (Celery tasks from notifications app)
    notify_vendor_new_order.delay(
        vendor_id=vendor_id,
        order_id=order.id,
        product_name=product.get("title") or f"Product #{product_id}",
        buyer_id=buyer_id,
        quantity=quantity,
    )
    notify_buyer_status.delay(
        buyer_id=buyer_id,
        order_id=order.id,
        status="pending",
        product_name=product.get("title") or f"Product #{product_id}",
    )

    return order


# Create or join a group order
# def create_or_join_group_order(
#     *, buyer_id: int, vendor_id: int, product_id: int, quantity: int,
#     unit_price: Decimal, payment_method: str, delivery_address: str,
#     subtotal: Decimal, delivery_fee: Decimal, total_amount: Decimal
# ):
#     product = get_product(product_id)
#     expected_subtotal = Decimal(product["group_price"]) * quantity
#     _price_guard(subtotal, expected_subtotal)

#     with transaction.atomic():
#         # Find an open group order for this product and lock it
#         go = (
#             GroupOrder.objects
#             .select_for_update()           # row lock while we update total_quantity  :contentReference[oaicite:5]{index=5}
#             .filter(product_id=product_id, status=GroupOrder.STATUS_OPEN)
#             .order_by("deadline")
#             .first()
#         )
#         if not go:
#             go = GroupOrder.objects.create(
#                 group_id=f"grp_{uuid.uuid4().hex[:12]}",
#                 product_id=product_id,
#                 total_quantity=0,
#                 deadline=timezone.now() + timezone.timedelta(hours=24),
#                 status=GroupOrder.STATUS_OPEN,
#             )
#         # increment total
#         go.total_quantity = F("total_quantity") + quantity
#         go.save(update_fields=["total_quantity"])

#         # Re-fetch to get actual value
#         go.refresh_from_db()

#         # Check min_quantity to possibly close the group
#         if go.total_quantity >= int(product["min_quantity"]):
#             go.status = GroupOrder.STATUS_CLOSED
#             go.save(update_fields=["status"])

#         # Check if buyer already has a pending order for this group+product
#         existing = (
#             Order.objects
#             .select_for_update()
#             .filter(user_id=buyer_id, group_id=go.group_id, status=Order.STATUS_PENDING)
#             .first()
#         )

#         if existing:
#             # Update item (single-product order per PHP logic)
#             item = existing.items.filter(product_id=product_id).first()
#             if item:
#                 item.quantity = F("quantity") + quantity
#                 item.price = Decimal(product["group_price"]) * (item.quantity + quantity)  # conservative
#                 item.save(update_fields=["quantity", "price"])
#             else:
#                 OrderItem.objects.create(
#                     order=existing, product_id=product_id, quantity=quantity,
#                     unit_price=Decimal(product["group_price"]),
#                     price=Decimal(product["group_price"]) * quantity
#                 )
#             # Recalculate order totals
#             existing.subtotal = subtotal  # from request (already validated)
#             existing.delivery_fee = delivery_fee
#             existing.total_amount = total_amount
#             existing.save(update_fields=["subtotal", "delivery_fee", "total_amount"])
#             order = existing
#         else:
#             order = Order.objects.create(
#                 user_id=buyer_id,
#                 vendor_id=vendor_id,
#                 group_id=go.group_id,
#                 subtotal=subtotal,
#                 delivery_fee=delivery_fee,
#                 total_amount=total_amount,
#                 payment_method=payment_method,
#                 delivery_address=delivery_address,
#                 status=Order.STATUS_PENDING,
#             )
#             OrderItem.objects.create(
#                 order=order,
#                 product_id=product_id,
#                 quantity=quantity,
#                 unit_price=Decimal(product["group_price"]),
#                 price=expected_subtotal,
#             )

#     # Side effects after commit
#     notify_vendor_new_order.delay(
#         vendor_id=vendor_id,
#         order_id=order.id,
#         product_name=product.get("title") or f"Product #{product_id}",
#         buyer_id=buyer_id,
#         quantity=quantity,
#     )
#     notify_buyer_status.delay(
#         buyer_id=buyer_id,
#         order_id=order.id,
#         status="pending",
#         product_name=product.get("title") or f"Product #{product_id}",
#     )

#     # Cache a small summary for quick UI reads (Redis)
#     cache_key = f"group:{go.group_id}:summary"
#     cache.set(cache_key, {"total_quantity": go.total_quantity, "status": go.status}, timeout=3600)  # django cache API  :contentReference[oaicite:6]{index=6}

#     return order, go

# Notes:
"""
    Why a “services” layer? Keeps your views thin and makes testing/business rules clear.
    Why atomic + select_for_update? To ensure correctness under concurrency (multiple buyers joining the same group simultaneously). 
    Django Project
"""