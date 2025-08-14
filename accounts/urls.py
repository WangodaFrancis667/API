# Add this to your urlpatterns

from .views import (
    UserDeleteView, ProfileUpdateView, LoginView, 
    UserSignUpView, UserLogoutView, UserProfileView, 
    TokenRefreshCookieView, status_view,
    PasswordResetRequestView, PasswordResetVerifyView,
    PasswordResetConfirmView, 
    )

from django.urls import path

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('signup/', UserSignUpView.as_view(), name='signup'),
    path('logout/', UserLogoutView.as_view(), name='logout'),

    path('status/', status_view, name='status'),
    path('token/refresh/', TokenRefreshCookieView.as_view(), name='refresh-token'),

    path('profile/', UserProfileView.as_view(), name='user-profile'),

    path('delete-account/', UserDeleteView.as_view(), name='delete-account'),
    path('update-profile/', ProfileUpdateView.as_view(), name='update-profile'),

    # Password reset endpoints
    # path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    # path('password-reset/verify/<str:uidb64>/<str:token>/', PasswordResetVerifyView.as_view(), name='password-reset-verify'),
    # path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # Password reset
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/verify/', PasswordResetVerifyView.as_view(), name='password-reset-verify'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

]