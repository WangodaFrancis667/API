# Add this to your urlpatterns

from .views import (
    UserDeleteView, ProfileUpdateView, LoginView, UserSignUpView
    )

from django.urls import path

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('signup/', UserSignUpView.as_view(), name='signup'),


    # ... existing urls
    path('delete-account/', UserDeleteView.as_view(), name='delete-account'),
    path('update-profile/', ProfileUpdateView.as_view(), name='update-profile'),
]