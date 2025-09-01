# payments/collections/urls.py
from django.urls import path
from .views import CollectionFeeView, CollectionOTPView, CollectionMoMoView

urlpatterns = [
    path("fees/", CollectionFeeView.as_view(), name="collection-fees"),
    path("otp/", CollectionOTPView.as_view(), name="collection-otp"),
    path("momo/", CollectionMoMoView.as_view(), name="collection-momo"),
]
