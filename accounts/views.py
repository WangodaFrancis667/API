# Add this to your existing views

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.db import models
import logging

from .models import User, AdminProfile, BuyerProfile, VendorProfile, UserActivityLog, ArchiveUser
from .serializers import (
    UserDeleteSerializer, ProfileUpdateSerializer, 
    UserRegistrationSerializer, VendorRegistrationSerializer,
    UserLoginSerializer, ProfileUpdateSerializer,
    UserProfileSerializer, PasswordChangeSerializer,
    AdminUserManagementSerializer, UserActivityLogSerializer,

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


# This is the login endpoint for all the users
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
class UserSignUpView(generics.GenericAPIView):
    """
    User registration endpoint with security validations.
    Only allows buyer registration. Vendors are created by admins.
    """
    serializer_class = UserRegistrationSerializer

    permission_classes = [AllowAny]
    throttle_scope = 'register'

    def post(self, request):
        # Register a new butyer

        # Rate limiting
        ip = self.get_client_ip(request)
        if not check_rate_limit(f"register:{ip}", 3, 300):  # 3 per 5 minutes
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