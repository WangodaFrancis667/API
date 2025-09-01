from django.urls import path
from .views import ForceUpdateView, StoreVersionsView

urlpatterns = [
    path("force-update", ForceUpdateView.as_view(), name="force_update"),
    path("store-versions", StoreVersionsView.as_view(), name="store_versions"),
]
