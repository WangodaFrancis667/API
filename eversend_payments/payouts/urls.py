from django.urls import path
from .views import PayoutView, PayoutQuotationView

urlpatterns = [
    path("payouts/", PayoutView.as_view(), name="payout"),
    path("payouts/quotation/", PayoutQuotationView.as_view(), name="payout-quotation"),
]
