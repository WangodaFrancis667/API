from django.urls import path

from .views import AppSettingsListsView, AppSettingsDetailView

urlpatterns = [
    path('app-settings/', AppSettingsListsView.as_view(), name='app-settings'),
    path('app-settings/<int:id>/', AppSettingsDetailView.as_view(), name='app-settings-detail'),
]