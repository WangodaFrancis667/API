from django.urls import path
from . import views

from .views import VendorStatsView

urlpatterns = [
    # Vendor-specific endpoints (support both vendor_name and vendor_id)
    path("stats/", VendorStatsView.as_view(), name="vendor_stats"),
    path("transactions/", views.vendor_transactions, name="vendor_transactions"),
    path("balance/", views.vendor_balance, name="vendor_balance"),
    path("earnings/", views.vendor_earnings_list, name="vendor_earnings_list"),
    path("payouts/", views.vendor_payouts_list, name="vendor_payouts_list"),
    # Admin endpoints
    path("all-vendors/", views.all_vendors_stats, name="all_vendors_stats"),
]
