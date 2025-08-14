# Add this to your existing views

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.decorators import api_view

from datetime import timezone, datetime

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.db import models

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.http import  JsonResponse
from django.shortcuts import render

import logging

from .models import User, AdminProfile, BuyerProfile, VendorProfile, UserActivityLog, ArchiveUser
from .serializers import (
    UserDeleteSerializer, ProfileUpdateSerializer, 
    UserRegistrationSerializer, VendorRegistrationSerializer,
    UserLoginSerializer, ProfileUpdateSerializer,
    UserProfileSerializer, PasswordChangeSerializer,
    AdminUserManagementSerializer, UserActivityLogSerializer,
    # PasswordResetRequestSerializer, PasswordResetConfirmSerializer,

    PasswordResetRequestSerializer, 
    PasswordResetVerifySerializer,
    PasswordResetConfirmSerializer

    )

from .permissions import (
    IsAdmin, IsVendor, IsBuyer, IsAdminOrVendor, IsVerifiedVendor,
    CanManageUsers, CanCreateVendor, IsAccountOwner, IsProfileOwner,
    PreventRoleEscalation, RateLimitPermission
)

from .security import (
    log_user_activity, cache_user_permissions, get_cached_user_permissions,
    invalidate_user_cache, check_rate_limit, is_suspicious_activity,
    get_user_dashboard_url
)

logger = logging.getLogger('accounts.security')
User = get_user_model()


def serialize_obj(obj):
    """Helper function to serialize objects to include only name and id."""
    if obj:
        return {"id": obj.id, "name": obj.name, "code": obj.code}
    return None


@api_view(['GET'])
def status_view(request):
    if not request.user.is_authenticated:
        return Response({'isAuthenticated': False}, status=status.HTTP_401_UNAUTHORIZED)
    
    user = request.user
    return Response({
        'isAuthenticated': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'profile_image': user.profile_image.url if user.profile_image else None,
        }
    })


# This is a token refresh view
class TokenRefreshCookieView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Try to get refresh token from the request body, then from cookies
        refresh_token = request.data.get("refresh") or request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"error": "Refresh token missing"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)
        except TokenError:
            return Response({"error": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)

        response = Response({"access": new_access_token}, status=status.HTTP_200_OK)
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=True,
            samesite="Lax"
        )
        return response


# This is the login endpoint for all the users
@method_decorator(csrf_exempt, name='dispatch')
class LoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            if serializer.is_valid():
                # Get validated data from serializer
                validated_data = serializer.validated_data

                # Return user data and tokens
                return Response(validated_data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            # log the exception
            logger.error(f"Login error: {str(e)}")

            return Response(
                {"error": "Authentication failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
            
        user_data = serializer.validated_data
        if not user_data:
            return Response(
                {"error": "User account not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        response = Response({
            "user": user_data["user"],
            "message": "Logged in successfully",
            "access": user_data["access"],
            "refresh": user_data["refresh"]
        }, status=status.HTTP_200_OK)
        
        response.set_cookie(
            key="access_token",
            value=user_data["access"],
            httponly=True,
            secure=True,  # Set to True in production (requires HTTPS)
            samesite="Lax",
        )
        response.set_cookie(
            key="refresh_token",
            value=user_data["refresh"],
            httponly=True,
            secure=True,
            samesite="Lax",
        )
        return response


# This is the user signup serializer
@method_decorator(csrf_exempt, name='dispatch')
class UserSignUpView(generics.GenericAPIView):
    """
    User registration endpoint with security validations.
    Only allows buyer registration. Vendors are created by admins.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'register'

    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    # Add GET method to show form in browsable API
    def get(self, request, *args, **kwargs):
        return Response({"message": "Please submit user registration data via POST"})

    def post(self, request):
        # Register a new butyer

        # Rate limiting
        ip = self.get_client_ip(request)
        if not check_rate_limit(f"register:{ip}", 10, 300):  # 10 per 5 minutes
            return Response(
                {"error": "Registration rate limit exceeded. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        serializer = UserRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    
                    # Generate tokens
                    refresh = RefreshToken.for_user(user)
                    
                    # Log registration
                    log_user_activity(
                        user, 
                        'REGISTRATION', 
                        'User registered successfully',
                        request
                    )
                    
                    # Cache user permissions
                    cache_user_permissions(user)
                    
                    return Response({
                        'message': 'Registration successful',
                        'user': UserProfileSerializer(user).data,
                        'tokens': {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                        },
                        'dashboard_url': get_user_dashboard_url(user)
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                logger.error(f"Registration error: {e}")
                return Response(
                    {"error": "Registration failed. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            # Return validation errors when serializer is invalid
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# This view is to log out the aythenticated user
class UserLogoutView(APIView):
    """
    User logout endpoint.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Logout user and blacklist refresh token."""
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Log logout
            log_user_activity(
                request.user, 
                'LOGOUT', 
                'User logged out successfully',
                request
            )
            response = Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            return response
        
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response(
                {"error": "Logout failed"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


# This is to allow a user to delete their account
class UserDeleteView(generics.GenericAPIView):
    """
    API endpoint for users to delete their own account.
    Requires password confirmation for security.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = UserDeleteSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# This is to allow a user to update their profile
class ProfileUpdateView(APIView):
    """
    API endpoint for users to update their profile information.
    Allows updating both base user fields and role-specific profile fields.
    """
    permission_classes = [IsAuthenticated]
    
    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            instance=request.user,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            # Return updated profile data
            profile_serializer = UserProfileSerializer(request.user)
            return Response(profile_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# This is a profile view
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    User profile view with role-based data and caching.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsAccountOwner]
    
    def get_object(self):
        """Get current user profile."""
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        """Update user profile with cache invalidation."""
        response = super().update(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Invalidate cache
            invalidate_user_cache(request.user.id)
            
            # Log profile update
            log_user_activity(
                request.user,
                'PROFILE_UPDATE',
                'User profile updated',
                request,
                {'fields_updated': list(request.data.keys())}
            )
        
        return response
    

# User password reset view
# class PasswordResetRequestView(generics.GenericAPIView):
#     """
#     Request a password reset email.
#     Sends a token via email that will be used to reset password.
#     """

#     serializer_class = PasswordResetRequestSerializer
#     permission_classes = [AllowAny]
#     throttle_scope = 'password_reset'

#     def post(self, request):
#         serializer = self.get_serializer(data=request.data)
#         if serializer.is_valid():
#             email = serializer.validated_data['email']
            
#             # Rate limiting
#             ip = request.META.get('REMOTE_ADDR', '')
#             if not check_rate_limit(f"password_reset:{ip}", 3, 3600):  # 3 per hour
#                 return Response(
#                     {"detail": "Too many password reset attempts. Please try again later."},
#                     status=status.HTTP_429_TOO_MANY_REQUESTS
#                 )
            
#             try:
#                 user = User.objects.get(email=email)
                
#                 # Generate password reset token
#                 token = default_token_generator.make_token(user)
#                 uid = urlsafe_base64_encode(force_bytes(user.pk))
                
#                 # Create reset URL
#                 frontend_url = settings.FRONTEND_URL
#                 reset_url = f"{frontend_url}/reset-password/{uid}/{token}/"
                
#                 # Send email
#                 subject = "Password Reset Request"
#                 email_template = "accounts/password_reset_email.html"
#                 email_context = {
#                     'user': user,
#                     'reset_url': reset_url,
#                     'site_name': settings.SITE_NAME,
#                     'valid_hours': 24,  # Token validity period
#                 }
                
#                 try:
#                     # Render email template
#                     html_message = render_to_string(email_template, email_context)
#                     plain_message = f"Password Reset Link: {reset_url}\nValid for 24 hours."
                    
#                     # Send email
#                     send_mail(
#                         subject=subject,
#                         message=plain_message,
#                         from_email=settings.DEFAULT_FROM_EMAIL,
#                         recipient_list=[email],
#                         html_message=html_message,
#                         fail_silently=False,
#                     )
                    
#                     # Log the password reset request
#                     log_user_activity(
#                         user,
#                         'PASSWORD_RESET_REQUEST',
#                         'Password reset requested',
#                         request
#                     )
                    
#                 except Exception as e:
#                     logger.error(f"Error sending password reset email: {str(e)}")
#                     return Response(
#                         {"detail": "Error sending password reset email. Please try again later."},
#                         status=status.HTTP_500_INTERNAL_SERVER_ERROR
#                     )
                
#                 # Always return success to prevent email enumeration
#                 return Response(
#                     {"detail": "Password reset email has been sent if the email exists in our system."},
#                     status=status.HTTP_200_OK
#                 )
                
#             except User.DoesNotExist:
#                 # Return a success message even if user doesn't exist (security)
#                 return Response(
#                     {"detail": "Password reset email has been sent if the email exists in our system."},
#                     status=status.HTTP_200_OK
#                 )
                
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class PasswordResetVerifyView(generics.GenericAPIView):
#     """
#     Verify password reset token.
#     Used to validate the token before showing the password reset form.
#     """
#     permission_classes = [AllowAny]
    
#     def get(self, request, uidb64, token):
#         try:
#             # Decode user ID
#             uid = force_str(urlsafe_base64_decode(uidb64))
#             user = User.objects.get(pk=uid)
            
#             # Verify token
#             if default_token_generator.check_token(user, token):
#                 return Response(
#                     {"detail": "Token is valid", "uidb64": uidb64, "token": token},
#                     status=status.HTTP_200_OK
#                 )
            
#             return Response(
#                 {"detail": "Invalid or expired token."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
            
#         except (TypeError, ValueError, OverflowError, User.DoesNotExist):
#             return Response(
#                 {"detail": "Invalid reset link."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )


# class PasswordResetConfirmView(generics.GenericAPIView):
#     """
#     Complete the password reset process.
#     Validates the token and sets the new password.
#     """
#     serializer_class = PasswordResetConfirmSerializer
#     permission_classes = [AllowAny]
    
#     def post(self, request):
#         serializer = self.get_serializer(data=request.data)
#         if serializer.is_valid():
#             try:
#                 # Get validated data
#                 token = serializer.validated_data['token']
#                 uidb64 = serializer.validated_data['uidb64']
#                 password = serializer.validated_data['password']
                
#                 # Decode user ID
#                 uid = force_str(urlsafe_base64_decode(uidb64))
#                 user = User.objects.get(pk=uid)
                
#                 # Verify token
#                 if not default_token_generator.check_token(user, token):
#                     return Response(
#                         {"detail": "Invalid or expired token."},
#                         status=status.HTTP_400_BAD_REQUEST
#                     )
                
#                 # Set new password
#                 user.set_password(password)
#                 user.login_attempts = 0  # Reset login attempts
#                 user.unlock_account()    # Unlock account if locked
#                 user.save()
                
#                 # Log password reset
#                 log_user_activity(
#                     user,
#                     'PASSWORD_RESET',
#                     'Password reset successful',
#                     request
#                 )
                
#                 # Invalidate user cache
#                 invalidate_user_cache(user.id)
                
#                 return Response(
#                     {"detail": "Password has been reset successfully."},
#                     status=status.HTTP_200_OK
#                 )
                
#             except (TypeError, ValueError, OverflowError, User.DoesNotExist):
#                 return Response(
#                     {"detail": "Invalid reset link."},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
                
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Add these views
class PasswordResetRequestView(generics.GenericAPIView):
    """
    Request a password reset via email or phone.
    """
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            email_or_phone = serializer.validated_data['email_or_phone']
            is_email = serializer.validated_data.get('is_email', True)
            
            # Rate limiting
            ip = request.META.get('REMOTE_ADDR', '')
            if not check_rate_limit(f"password_reset:{ip}", 3, 3600):  # 3 per hour
                return Response(
                    {"detail": "Too many password reset attempts. Please try again later."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
                
            # Try to get the user
            try:
                if is_email:
                    user = User.objects.get(email=email_or_phone.lower())
                else:
                    user = User.objects.get(phone=email_or_phone)
                
                # Generate token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
                
                # Send notification (email or SMS)
                if is_email and user.email:
                    self._send_reset_email(user, reset_url)
                elif user.phone:
                    self._send_reset_sms(user, reset_url)
                
                # Log activity
                log_user_activity(
                    user,
                    'PASSWORD_RESET_REQUEST',
                    f"Password reset requested via {'email' if is_email else 'phone'}",
                    request
                )
                
            except User.DoesNotExist:
                # We don't reveal if the user exists for security
                pass
            
            # Always return success to prevent enumeration attacks
            return Response(
                {"detail": "If a matching account was found, a password reset link has been sent."},
                status=status.HTTP_200_OK
            )
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def _send_reset_email(self, user, reset_url):
        """Send password reset email."""
        subject = f"{settings.SITE_NAME} - Password Reset"
        html_message = render_to_string('accounts/password_reset_email.html', {
            'user': user,
            'reset_url': reset_url,
            'site_name': settings.SITE_NAME,
            'valid_hours': 24
        })
        plain_message = f"Password Reset Link: {reset_url}\nValid for 24 hours."
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Password reset email sent to: {user.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
    
    def _send_reset_sms(self, user, reset_url):
        """Send password reset SMS."""
        # Implement SMS sending logic here
        # This is just a placeholder - you'll need to integrate with an SMS service
        message = f"{settings.SITE_NAME}: Reset your password with this link: {reset_url}"
        logger.info(f"Password reset SMS would be sent to: {user.phone}")
        # In a real implementation, call your SMS service here


class PasswordResetVerifyView(generics.GenericAPIView):
    """
    Verify a password reset token is valid.
    Used to check before showing the password reset form.
    """
    serializer_class = PasswordResetVerifySerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            token = serializer.validated_data['token']
            uidb64 = serializer.validated_data['uidb64']
            
            try:
                uid = force_str(urlsafe_base64_decode(uidb64))
                user = User.objects.get(pk=uid)
                
                if default_token_generator.check_token(user, token):
                    return Response(
                        {"detail": "Token is valid", "uidb64": uidb64, "token": token},
                        status=status.HTTP_200_OK
                    )
                
                return Response(
                    {"detail": "Invalid or expired token."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                return Response(
                    {"detail": "Invalid reset link."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(generics.GenericAPIView):
    """
    Reset password with a valid token.
    """
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            token = serializer.validated_data['token']
            uidb64 = serializer.validated_data['uidb64']
            new_password = serializer.validated_data['new_password']
            
            try:
                uid = force_str(urlsafe_base64_decode(uidb64))
                user = User.objects.get(pk=uid)
                
                if default_token_generator.check_token(user, token):
                    # Set new password
                    user.set_password(new_password)
                    
                    # Reset account security
                    user.login_attempts = 0
                    if user.is_account_locked():
                        user.unlock_account()
                    
                    user.save()
                    
                    # Log activity
                    log_user_activity(
                        user,
                        'PASSWORD_RESET_COMPLETE',
                        "Password reset completed successfully",
                        request
                    )
                    
                    # Invalidate user cache
                    invalidate_user_cache(user.id)
                    
                    return Response(
                        {"detail": "Password has been reset successfully."},
                        status=status.HTTP_200_OK
                    )
                
                return Response(
                    {"detail": "Invalid or expired token."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                return Response(
                    {"detail": "Invalid reset link."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# Admin vendor registration view
class VendorRegistrationView(generics.GenericAPIView):
    """
    Vendor registration endpoint (Admin only).
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        """Create a new vendor user (Admin only)."""
        serializer = VendorRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    vendor_user = serializer.save()
                    
                    # Log vendor creation
                    log_user_activity(
                        request.user,
                        'VENDOR_CREATED',
                        f'Vendor account created: {vendor_user.username}',
                        request,
                        {'created_user_id': vendor_user.id}
                    )
                    
                    return Response({
                        'message': 'Vendor created successfully',
                        'vendor': UserProfileSerializer(vendor_user).data
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                logger.error(f"Vendor creation error: {e}")
                return Response(
                    {"error": "Vendor creation failed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserManagementView(generics.ListCreateAPIView):
    """
    Admin endpoint for user management.
    """
    serializer_class = AdminUserManagementSerializer
    permission_classes = [IsAuthenticated, CanManageUsers]
    
    def get_queryset(self):
        """Get users with optional filtering."""
        queryset = User.objects.select_related('admin_profile', 'vendor_profile', 'buyer_profile')
        
        # Filter by role
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(username__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search)
            )
        
        return queryset.order_by('-date_joined')


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin endpoint for individual user management.
    """
    serializer_class = AdminUserManagementSerializer
    permission_classes = [IsAuthenticated, CanManageUsers]
    queryset = User.objects.all()
    
    def update(self, request, *args, **kwargs):
        """Update user with logging and cache invalidation."""
        user = self.get_object()
        old_data = {
            'role': user.role,
            'status': user.status,
            'is_active': user.is_active
        }
        
        response = super().update(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Invalidate cache for updated user
            invalidate_user_cache(user.id)
            
            # Log admin action
            log_user_activity(
                request.user,
                'USER_UPDATED',
                f'User {user.username} updated by admin',
                request,
                {
                    'target_user_id': user.id,
                    'old_data': old_data,
                    'new_data': request.data
                }
            )
        
        return response
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete user instead of hard delete."""
        user = self.get_object()
        
        # Soft delete - deactivate instead of delete
        user.is_active = False
        user.status = 'inactive'
        user.save()
        
        # Invalidate cache
        invalidate_user_cache(user.id)
        
        # Log admin action
        log_user_activity(
            request.user,
            'USER_DEACTIVATED',
            f'User {user.username} deactivated by admin',
            request,
            {'target_user_id': user.id}
        )
        
        return Response(
            {"message": "User deactivated successfully"}, 
            status=status.HTTP_200_OK
        )


class VendorVerificationView(APIView):
    """
    Admin endpoint for vendor verification.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, user_id):
        """Verify or unverify a vendor."""
        try:
            user = User.objects.get(id=user_id, role='vendor')
            vendor_profile = user.vendor_profile
            
            action = request.data.get('action')  # 'verify' or 'unverify'
            
            if action == 'verify':
                vendor_profile.is_verified_vendor = True
                user.status = 'active'
                log_message = f'Vendor {user.username} verified'
            elif action == 'unverify':
                vendor_profile.is_verified_vendor = False
                user.status = 'pending'
                log_message = f'Vendor {user.username} unverified'
            else:
                return Response(
                    {"error": "Invalid action. Use 'verify' or 'unverify'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            vendor_profile.save()
            user.save()
            
            # Invalidate cache
            invalidate_user_cache(user.id)
            
            # Log admin action
            log_user_activity(
                request.user,
                'VENDOR_VERIFICATION',
                log_message,
                request,
                {'target_user_id': user.id, 'action': action}
            )
            
            return Response({
                'message': log_message,
                'vendor': UserProfileSerializer(user).data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "Vendor not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Vendor verification error: {e}")
            return Response(
                {"error": "Verification failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserActivityLogView(generics.ListAPIView):
    """
    View user activity logs (Admin can see all, users can see their own).
    """
    serializer_class = UserActivityLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get activity logs based on user role."""
        if self.request.user.role == 'admin':
            queryset = UserActivityLog.objects.all()
            
            # Filter by user
            user_id = self.request.query_params.get('user_id')
            if user_id:
                queryset = queryset.filter(user_id=user_id)
            
            # Filter by action
            action = self.request.query_params.get('action')
            if action:
                queryset = queryset.filter(action=action)
            
        else:
            # Users can only see their own logs
            queryset = UserActivityLog.objects.filter(user=self.request.user)
        
        return queryset.order_by('-created_at')


class DashboardStatsView(APIView):
    """
    Dashboard statistics with caching.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get dashboard statistics based on user role."""
        user = request.user
        cache_key = f"dashboard_stats_{user.role}_{user.id}"
        
        stats = cache.get(cache_key)
        if stats is None:
            if user.role == 'admin':
                stats = self._get_admin_stats()
            elif user.role == 'vendor':
                stats = self._get_vendor_stats(user)
            elif user.role == 'buyer':
                stats = self._get_buyer_stats(user)
            else:
                stats = {}
            
            cache.set(cache_key, stats, 300)  # Cache for 5 minutes
        
        return Response(stats, status=status.HTTP_200_OK)
    
    def _get_admin_stats(self):
        """Get admin dashboard statistics."""
        return {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(status='active').count(),
            'pending_users': User.objects.filter(status='pending').count(),
            'total_admins': User.objects.filter(role='admin').count(),
            'total_vendors': User.objects.filter(role='vendor').count(),
            'verified_vendors': User.objects.filter(
                role='vendor', 
                vendor_profile__is_verified_vendor=True
            ).count(),
            'total_buyers': User.objects.filter(role='buyer').count(),
            'recent_registrations': User.objects.filter(
                date_joined__gte=timezone.now() - timezone.timedelta(days=7)
            ).count()
        }
    
    def _get_vendor_stats(self, user):
        """Get vendor dashboard statistics."""
        return {
            'verification_status': getattr(user.vendor_profile, 'is_verified_vendor', False),
            'wallet_balance': float(user.wallet),
            'account_status': user.status,
            'profile_completion': self._calculate_profile_completion(user)
        }
    
    def _get_buyer_stats(self, user):
        """Get buyer dashboard statistics."""
        return {
            'wallet_balance': float(user.wallet),
            'referral_points': user.referral_points,
            'loyalty_tier': getattr(user.buyer_profile, 'loyalty_tier', 'bronze'),
            'account_status': user.status,
            'profile_completion': self._calculate_profile_completion(user)
        }
    
    def _calculate_profile_completion(self, user):
        """Calculate profile completion percentage."""
        fields = ['first_name', 'last_name', 'email', 'phone', 'location']
        completed = sum(1 for field in fields if getattr(user, field))
        return int((completed / len(fields)) * 100)

   


@csrf_exempt
def user_permissions(request):
    """
    Get current user permissions.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        permissions_data = get_cached_user_permissions(request.user)
        return JsonResponse(permissions_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

