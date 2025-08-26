from django.urls import path
from .views import placeholder

urlpatterns = [
    path('test', placeholder, name='test')
]