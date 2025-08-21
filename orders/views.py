from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .serializers import (
    OrderCreateSerializer, OrderResponseSerializer,
)

from .services import (
    create_or_join_group_order, create_individual_order,
)

class CreateOrderView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]  # adjust as needed

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data.get("is_group_order"):
            order, go = create_or_join_group_order(
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
                "group_id": order.group_id,
                "total_amount": str(order.total_amount),
                "payment_method": order.payment_method,
                "is_group_order": True,
            }
        else:
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
                "group_id": order.group_id,
                "total_amount": str(order.total_amount),
                "payment_method": order.payment_method,
                "is_group_order": False,
            }

        return Response({"status": "success", "message": "Order placed successfully", "data": payload},
                        status=status.HTTP_201_CREATED)