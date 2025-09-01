from django.urls import path
from . import views

from .views import VendorStatsView

urlpatterns = [
    path("stats/", VendorStatsView.as_view(), name="vendor_stats"),
    path("transactions/", views.vendor_transactions, name="vendor_transactions"),
    path("balance/", views.vendor_balance, name="vendor_balance"),
]
