# notifications/urls.py
from django.urls import path
from .views  import (
    ListNotificationsView, UnreadCountView, MarkAsReadView,
    MarkAllAsReadView, DeleteNotificationView, DeleteAllForUserView,
    PhoneNotificationsView, CreateCustomNotificationView
)

urlpatterns = [
    path('', ListNotificationsView.as_view(), name='notif-list'),
    path('unread-count/', UnreadCountView.as_view(), name='notif-unread-count'),
    path('mark-read/', MarkAsReadView.as_view(), name='notif-mark-read'),
    path('mark-all-read/', MarkAllAsReadView.as_view(), name='notif-mark-all'),
    path('delete/', DeleteNotificationView.as_view(), name='notif-delete'),
    path('delete-all/', DeleteAllForUserView.as_view(), name='notif-delete-all'),
    path('by-phone/', PhoneNotificationsView.as_view(), name='notif-by-phone'),
    path('custom/', CreateCustomNotificationView.as_view(), name='notif-create-custom'),
]
