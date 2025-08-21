from django.urls import path

from .views import (
    CreateOrderView, OrderListView, UpdateOrderStatusView, 
    CreateReturnView
)

urlpatterns = [
    path("create/", CreateOrderView.as_view(), name="orders-create"),
    path("list/", OrderListView.as_view(), name="orders-list"),
    path("status/", UpdateOrderStatusView.as_view(), name="orders-update-status"),
    path("return/", CreateReturnView.as_view(), name="orders-create-return"),
]
