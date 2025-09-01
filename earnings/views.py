from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny

from django.db.models import Count, Sum
from orders.models import Order
from django.contrib.auth import get_user_model

from .serializers import OrderSerializer
from .utils import get_date_range

Vendor = get_user_model()


class VendorStatsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get(self, request):
        vendor_id = request.query_params.get("vendor_id")
        period = request.query_params.get("period")

        if not vendor_id or not period:
            return Response(
                {
                    "status": "error",
                    "message": "Missing or invalid required parameters",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            vendor = Vendor.objects.get(pk=vendor_id)
        except Vendor.DoesNotExist:
            return Response(
                {"status": "error", "message": "Vendor not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        start_date, end_date = get_date_range(period)

        stats = Order.objects.filter(
            vendor=vendor, status="completed", created_at__range=(start_date, end_date)
        ).aggregate(order_count=Count("id"), total_sales=Sum("total_amount"))

        return Response(
            {
                "status": "success",
                "stats": {
                    "order_count": stats["order_count"] or 0,
                    "total_sales": float(stats["total_sales"] or 0),
                },
            }
        )


@api_view(["POST"])
def vendor_transactions(request):
    vendor_id = request.data.get("vendor_id")
    period = request.data.get("period")

    if not vendor_id or not period:
        return Response(
            {"status": "error", "message": "Missing or invalid required parameters"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        vendor = Vendor.objects.get(pk=vendor_id)
    except Vendor.DoesNotExist:
        return Response(
            {"status": "error", "message": "Vendor not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    start_date, end_date = get_date_range(period)

    transactions = Order.objects.filter(
        vendor=vendor, status="completed", created_at__range=(start_date, end_date)
    ).order_by("-created_at")

    serializer = OrderSerializer(transactions, many=True)
    return Response({"status": "success", "transactions": serializer.data})


@api_view(["POST"])
def vendor_balance(request):
    vendor_id = request.data.get("vendor_id")

    if not vendor_id:
        return Response(
            {"status": "error", "message": "Missing or invalid vendor_id"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        vendor = Vendor.objects.get(pk=vendor_id)
    except Vendor.DoesNotExist:
        return Response(
            {"status": "error", "message": "Vendor not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response({"status": "success", "balance": float(vendor.wallet)})
