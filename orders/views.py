from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination

from django.shortcuts import get_object_or_404

from .serializers import (
    OrderCreateSerializer,
    OrderResponseSerializer,
    UpdateOrderStatusSerializer,
    OrderReturnCreateSerializer,
)

from accounts.permissions import (
    IsAdmin,
    IsVendor,
    IsBuyer,
    IsAdminOrVendor,
    IsVerifiedVendor,
    CanManageUsers,
    CanCreateVendor,
    IsAccountOwner,
    IsProfileOwner,
    PreventRoleEscalation,
    RateLimitPermission,
)

from .services import (
    # create_or_join_group_order,
    create_individual_order,
)

from .tasks import notify_buyer_on_status_change, notify_admin_return_request


from .models import Order, OrderReturn


class CreateOrderView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]  # adjust as needed

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            # if data.get("is_group_order"):
            #     order, go = create_or_join_group_order(
            #         buyer_id=data["buyer_id"],
            #         vendor_id=data["vendor_id"],
            #         product_id=data["item"]["product_id"],
            #         quantity=data["item"]["quantity"],
            #         unit_price=data["item"]["unit_price"],
            #         payment_method=data["payment_method"],
            #         delivery_address=data["delivery_address"],
            #         subtotal=data["subtotal"],
            #         delivery_fee=data["delivery_fee"],
            #         total_amount=data["total_amount"],
            #     )
            #     payload = {
            #         "order_id": order.id,
            #         "group_id": order.group_id,
            #         "total_amount": str(order.total_amount),
            #         "payment_method": order.payment_method,
            #         "is_group_order": True,
            #     }
            # else:
            order = create_individual_order(
                buyer_id=data["buyer_id"],
                vendor_id=data["vendor_id"],
                product_id=data["item"]["product_id"],
                quantity=data["item"]["quantity"],
                unit_price=data["item"]["unit_price"],
                payment_method=data["payment_method"],
                delivery_address=data["delivery_address"],
                subtotal=data["subtotal"],
                delivery_fee=data["delivery_fee"],
                total_amount=data["total_amount"],
            )
            payload = {
                "order_id": order.id,
                # "group_id": order.group_id,
                "total_amount": str(order.total_amount),
                "payment_method": order.payment_method,
                "is_group_order": False,
            }
        except ValueError as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "status": "success",
                "message": "Order placed successfully",
                "data": payload,
            },
            status=status.HTTP_201_CREATED,
        )


class OrderListView(generics.ListAPIView):
    """
    Lists orders visible to the requesting user.
    Buyers see their orders; vendors see orders matching their vendor_id.
    """

    serializer_class = OrderResponseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LimitOffsetPagination  # Recommended pagination style :contentReference[oaicite:0]{index=0}

    def get_queryset(self):
        user = self.request.user
        # For simplicity, assume user.role indicates buyer/vendor
        if user.role == "buyer":
            return Order.objects.filter(user=user).order_by("-created_at")
        elif user.role == "vendor":
            return Order.objects.filter(vendor_id=user.id).order_by("-created_at")
        else:
            return Order.objects.none()


class UpdateOrderStatusView(generics.GenericAPIView):
    permission_classes = [IsAdminOrVendor]

    def post(self, request):
        serializer = UpdateOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = get_object_or_404(Order, id=serializer.validated_data["order_id"])

        # Only allow vendor to update their own order
        if (
            request.user.role != "vendor" and request.user.role != "admin"
        ):  # or order.vendor_id != request.user.id:
            return Response(
                {"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN
            )

        old_status = order.status
        new_status = serializer.validated_data["new_status"]
        old_status = new_status
        order.save(update_fields=["status", "updated_at"])

        # Send notification to buyer
        notify_buyer_on_status_change.delay(
            buyer_id=order.user_id,
            order_id=order.id,
            status=new_status,
            product_name=f"Order #{order.id}",
        )

        return Response(
            {"status": "success", "message": f"Order status updated to {new_status}"}
        )


class CreateReturnView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OrderReturnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = get_object_or_404(Order, id=serializer.validated_data["order_id"])

        # Only buyer can request return
        if request.user.id != order.user_id:
            return Response(
                {"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN
            )

        return_obj = OrderReturn.objects.create(
            order=order,
            user=request.user,
            return_reason=serializer.validated_data["return_reason"],
            return_status=OrderReturn.STATUS_PENDING,
        )

        notify_admin_return_request.delay(
            order_id=order.id, return_id=return_obj.id, buyer_id=request.user.id
        )

        return Response({"status": "success", "message": "Return request submitted."})
