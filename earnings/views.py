from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from django.db.models import Count, Sum, Q
from django.shortcuts import get_object_or_404
from orders.models import Order
from django.contrib.auth import get_user_model

from .serializers import (
    OrderSerializer,
    VendorEarningsSerializer,
    VendorPayoutSerializer,
    VendorEarningSummarySerializer,
)
from .models import VendorEarnings, VendorPayout, VendorEarningSummary
from .utils import get_date_range

User = get_user_model()


class VendorStatsView(generics.GenericAPIView):
    """
    Get vendor statistics for a specific period
    Supports both vendor_name and vendor_id for flexibility
    Endpoint: GET /api/earnings/stats/?vendor_name=john_vendor&period=this_month
    Endpoint: GET /api/earnings/stats/?vendor_id=123&period=this_month
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        vendor_id = request.query_params.get("vendor_id")
        vendor_name = request.query_params.get("vendor_name")
        period = request.query_params.get("period", "this_month")

        if not vendor_id and not vendor_name:
            return Response(
                {
                    "status": "error",
                    "message": "Either vendor_id or vendor_name parameter is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get vendor using either ID or username (both are indexed)
        if vendor_name:
            vendor = get_object_or_404(User, username=vendor_name, role="vendor")
        else:
            vendor = get_object_or_404(User, pk=vendor_id, role="vendor")

        # Get date range
        start_date, end_date = get_date_range(period)

        # Get stats for completed orders
        order_stats = Order.objects.filter(
            vendor=vendor,
            status=Order.STATUS_COMPLETED,
            created_at__range=(start_date, end_date),
        ).aggregate(order_count=Count("id"), total_sales=Sum("total_amount"))

        # Get earnings stats
        earnings_stats = VendorEarnings.objects.filter(
            vendor=vendor, created_at__range=(start_date, end_date)
        ).aggregate(
            total_commission=Sum("commission_amount"),
            total_net_earnings=Sum("net_earnings"),
        )

        # Get earnings by status
        pending_earnings = (
            VendorEarnings.objects.filter(
                vendor=vendor,
                created_at__range=(start_date, end_date),
                status=VendorEarnings.STATUS_PENDING,
            ).aggregate(total=Sum("net_earnings"))["total"]
            or 0
        )

        paid_earnings = (
            VendorEarnings.objects.filter(
                vendor=vendor,
                created_at__range=(start_date, end_date),
                status=VendorEarnings.STATUS_PAID,
            ).aggregate(total=Sum("net_earnings"))["total"]
            or 0
        )

        return Response(
            {
                "status": "success",
                "vendor": {
                    "id": vendor.id,
                    "username": vendor.username,
                    "business_name": vendor.business_name,
                    "wallet_balance": float(vendor.wallet),
                },
                "period": period,
                "stats": {
                    "order_count": order_stats["order_count"] or 0,
                    "total_sales": float(order_stats["total_sales"] or 0),
                    "total_commission": float(earnings_stats["total_commission"] or 0),
                    "net_earnings": float(earnings_stats["total_net_earnings"] or 0),
                    "pending_earnings": float(pending_earnings),
                    "paid_earnings": float(paid_earnings),
                },
            }
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_transactions(request):
    """
    Get vendor transactions/orders for a specific period
    Endpoint: GET /api/earnings/transactions/?vendor_name=john_vendor&period=this_month
    Endpoint: GET /api/earnings/transactions/?vendor_id=123&period=this_month
    """
    vendor_id = request.query_params.get("vendor_id")
    vendor_name = request.query_params.get("vendor_name")
    period = request.query_params.get("period", "this_month")

    if not vendor_id and not vendor_name:
        return Response(
            {
                "status": "error",
                "message": "Either vendor_id or vendor_name parameter is required",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get vendor using either ID or username
    if vendor_name:
        vendor = get_object_or_404(User, username=vendor_name, role="vendor")
    else:
        vendor = get_object_or_404(User, pk=vendor_id, role="vendor")

    start_date, end_date = get_date_range(period)

    transactions = Order.objects.filter(
        vendor=vendor,
        status=Order.STATUS_COMPLETED,
        created_at__range=(start_date, end_date),
    ).order_by("-created_at")

    serializer = OrderSerializer(transactions, many=True)
    return Response(
        {"status": "success", "period": period, "transactions": serializer.data}
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_balance(request):
    """
    Get vendor wallet balance
    Endpoint: GET /api/earnings/balance/?vendor_name=john_vendor
    Endpoint: GET /api/earnings/balance/?vendor_id=123
    """
    vendor_id = request.query_params.get("vendor_id")
    vendor_name = request.query_params.get("vendor_name")

    if not vendor_id and not vendor_name:
        return Response(
            {
                "status": "error",
                "message": "Either vendor_id or vendor_name parameter is required",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get vendor using either ID or username
    if vendor_name:
        vendor = get_object_or_404(User, username=vendor_name, role="vendor")
    else:
        vendor = get_object_or_404(User, pk=vendor_id, role="vendor")

    # Get additional balance info
    pending_earnings = (
        VendorEarnings.objects.filter(
            vendor=vendor, status=VendorEarnings.STATUS_PENDING
        ).aggregate(total=Sum("net_earnings"))["total"]
        or 0
    )

    return Response(
        {
            "status": "success",
            "vendor": {
                "id": vendor.id,
                "username": vendor.username,
                "business_name": vendor.business_name,
            },
            "balance": {
                "wallet_balance": float(vendor.wallet),
                "pending_earnings": float(pending_earnings),
                "total_available": float(vendor.wallet) + float(pending_earnings),
            },
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_earnings_list(request):
    """
    Get detailed list of vendor earnings
    Endpoint: GET /api/earnings/earnings/?vendor_name=john_vendor&period=this_month
    Endpoint: GET /api/earnings/earnings/?vendor_id=123&period=this_month
    """
    vendor_id = request.query_params.get("vendor_id")
    vendor_name = request.query_params.get("vendor_name")
    period = request.query_params.get("period", "this_month")

    if not vendor_id and not vendor_name:
        return Response(
            {
                "status": "error",
                "message": "Either vendor_id or vendor_name parameter is required",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get vendor using either ID or username
    if vendor_name:
        vendor = get_object_or_404(User, username=vendor_name, role="vendor")
    else:
        vendor = get_object_or_404(User, pk=vendor_id, role="vendor")
    start_date, end_date = get_date_range(period)

    earnings = VendorEarnings.objects.filter(
        vendor=vendor, created_at__range=(start_date, end_date)
    ).order_by("-created_at")

    serializer = VendorEarningsSerializer(earnings, many=True)
    return Response(
        {"status": "success", "period": period, "earnings": serializer.data}
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_payouts_list(request):
    """
    Get list of vendor payouts
    Endpoint: GET /api/earnings/payouts/?vendor_name=john_vendor
    Endpoint: GET /api/earnings/payouts/?vendor_id=123
    """
    vendor_id = request.query_params.get("vendor_id")
    vendor_name = request.query_params.get("vendor_name")

    if not vendor_id and not vendor_name:
        return Response(
            {
                "status": "error",
                "message": "Either vendor_id or vendor_name parameter is required",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get vendor using either ID or username
    if vendor_name:
        vendor = get_object_or_404(User, username=vendor_name, role="vendor")
    else:
        vendor = get_object_or_404(User, pk=vendor_id, role="vendor")

    payouts = VendorPayout.objects.filter(vendor=vendor).order_by("-created_at")

    serializer = VendorPayoutSerializer(payouts, many=True)
    return Response({"status": "success", "payouts": serializer.data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def all_vendors_stats(request):
    """
    Get statistics for all vendors (Admin only)
    Endpoint: GET /api/earnings/all-vendors/?period=this_month
    """
    # Check if user is admin
    if not request.user.role == "admin":
        return Response(
            {"status": "error", "message": "Admin access required"},
            status=status.HTTP_403_FORBIDDEN,
        )

    period = request.query_params.get("period", "this_month")
    start_date, end_date = get_date_range(period)

    # Get all vendors
    vendors = User.objects.filter(role="vendor")
    vendor_stats = []

    for vendor in vendors:
        order_stats = Order.objects.filter(
            vendor=vendor,
            status=Order.STATUS_COMPLETED,
            created_at__range=(start_date, end_date),
        ).aggregate(order_count=Count("id"), total_sales=Sum("total_amount"))

        earnings_stats = VendorEarnings.objects.filter(
            vendor=vendor, created_at__range=(start_date, end_date)
        ).aggregate(net_earnings=Sum("net_earnings"))

        vendor_stats.append(
            {
                "vendor": {
                    "id": vendor.id,
                    "username": vendor.username,
                    "business_name": vendor.business_name,
                    "email": vendor.email,
                },
                "stats": {
                    "order_count": order_stats["order_count"] or 0,
                    "total_sales": float(order_stats["total_sales"] or 0),
                    "net_earnings": float(earnings_stats["net_earnings"] or 0),
                },
            }
        )

    return Response({"status": "success", "period": period, "vendors": vendor_stats})
