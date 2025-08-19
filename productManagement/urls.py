from django.urls import path
from .views import CategoriesListView

urlpatterns = [
    path('view-categories/', CategoriesListView.as_view(), name='view-categories'),
]