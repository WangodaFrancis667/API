from django.urls import path, include
from .views import EversendTokenView, EversendWebhookView

urlpatterns = [
    path("eversend/token/", EversendTokenView.as_view(), name="eversend-token"),
    path("webhooks/eversend/", EversendWebhookView.as_view(), name="eversend-webhook"),

    #collections
    path("collections/", include("eversend_payments.collections.urls")),
]