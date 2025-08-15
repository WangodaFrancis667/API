# Add this to your urlpatterns

from .views import (
    UserDeleteView, ProfileUpdateView, LoginView, 
    UserSignUpView, UserLogoutView, UserProfileView, 
    TokenRefreshCookieView, status_view,
    PasswordResetRequestView, PasswordResetVerifyView,
    PasswordResetConfirmView, VendorRegistrationView,
    AdminUserManagementView, AdminUserDetailView, 
    VendorVerificationView, UserActivityLogView,
    DashboardStatsView, SendEmailVerificationView,
    ConfirmEmailVerificationView, AddEmailView,


    )

from django.urls import path

urlpatterns = [
    # Authentication endpoints
    path('login/', LoginView.as_view(), name='login'),
    path('signup/', UserSignUpView.as_view(), name='signup'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('status/', status_view, name='status'),
    path('token/refresh/', TokenRefreshCookieView.as_view(), name='refresh-token'),

    # profile management endpoints
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('update-profile/', ProfileUpdateView.as_view(), name='update-profile'),

    # Account management endpoints
    path('delete-account/', UserDeleteView.as_view(), name='delete-account'),

    # Admin endpoints
    path('admin/users/', AdminUserManagementView.as_view(), name='admin-users'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/vendor/create/', VendorRegistrationView.as_view(), name='admin-create-vendor'),
    path('admin/vendor/<int:user_id>/verify/', VendorVerificationView.as_view(), name='vendor-verify'),

    # Activity logs
    path('activity-logs/', UserActivityLogView.as_view(), name='activity-logs'),
    
    # Dashboard
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    

    # Email verification endpoints
    path('add-email/', AddEmailView.as_view(), name='add-email'),
    path('email/send/', SendEmailVerificationView.as_view(), name='send-email-verification'),
    path('email/confirm/', ConfirmEmailVerificationView.as_view(), name='confirm-email-verification'),
    
    # Password reset
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/verify/', PasswordResetVerifyView.as_view(), name='password-reset-verify'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

]