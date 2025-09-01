from django.urls import path
from .views import ForceUpdateView

urlpatterns = [
    path("force-update", ForceUpdateView.as_view(), name="force_update"),
]
