"""
Custom permissions for role-based access control and security.
"""
from rest_framework import permissions
from django.core.cache import cache
import logging

logger = logging.getLogger('accounts.security')


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` attribute.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Instance must have an attribute named `owner`.
        return obj.user == request.user


class IsAdmin(permissions.BasePermission):
    """
    Allows access only to admin users.
    """
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')


class IsVendor(permissions.BasePermission):
    """
    Allows access only to vendor users.
    """
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'vendor')


class IsBuyer(permissions.BasePermission):
    """
    Allows access only to buyer users.
    """
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'buyer')


class IsAdminOrVendor(permissions.BasePermission):
    """
    Allows access to admin or vendor users.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'vendor']
        )


class IsVerifiedVendor(permissions.BasePermission):
    """
    Allows access only to verified vendor users.
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.role == 'vendor'):
            return False
        
        # Cache the verification status
        cache_key = f"vendor_verified_{request.user.id}"
        is_verified = cache.get(cache_key)
        
        if is_verified is None:
            try:
                is_verified = request.user.vendor_profile.is_verified_vendor
                cache.set(cache_key, is_verified, 300)  # Cache for 5 minutes
            except:
                is_verified = False
                cache.set(cache_key, is_verified, 60)  # Cache shorter for error cases
        
        return is_verified


class CanManageUsers(permissions.BasePermission):
    """
    Permission for user management operations.
    Only admins can create/edit/delete users.
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Only admins can manage users
        if request.user.role != 'admin':
            return False
        
        # Log admin actions
        logger.info(f"Admin {request.user.username} accessing user management: {request.method} {view.__class__.__name__}")
        return True


class CanCreateVendor(permissions.BasePermission):
    """
    Permission to create vendor accounts.
    Only admins can create vendor accounts.
    """
    
    def has_permission(self, request, view):
        if request.method == 'POST' and request.data.get('role') == 'vendor':
            return bool(
                request.user and 
                request.user.is_authenticated and 
                request.user.role == 'admin'
            )
        return True


class IsAccountOwner(permissions.BasePermission):
    """
    Permission to ensure users can only access their own account data.
    Admins can access any account for management purposes.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin can access any user's data
        if request.user.role == 'admin':
            return True
        
        # Users can only access their own data
        return obj == request.user


class IsProfileOwner(permissions.BasePermission):
    """
    Permission to ensure users can only access their own profile data.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin can access any profile
        if request.user.role == 'admin':
            return True
        
        # Users can only access their own profile
        return obj.user == request.user


class PreventRoleEscalation(permissions.BasePermission):
    """
    Prevent users from escalating their own roles or privileges.
    """
    
    def has_permission(self, request, view):
        # Allow if not trying to modify role
        if 'role' not in request.data:
            return True
        
        # Only admins can modify roles
        if request.user.role != 'admin':
            logger.warning(f"User {request.user.username} attempted role escalation")
            return False
        
        return True


class RateLimitPermission(permissions.BasePermission):
    """
    Custom rate limiting permission with Redis caching.
    """
    
    def has_permission(self, request, view):
        if not hasattr(view, 'throttle_scope'):
            return True
        
        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        cache_key = f"rate_limit_{view.throttle_scope}_{ip}"
        current_requests = cache.get(cache_key, 0)
        
        # Define rate limits
        limits = {
            'login': 5,  # 5 per minute
            'register': 3,  # 3 per minute
            'password_reset': 3,  # 3 per minute
        }
        
        limit = limits.get(view.throttle_scope, 10)
        
        if current_requests >= limit:
            logger.warning(f"Rate limit exceeded for {ip} on {view.throttle_scope}")
            return False
        
        # Increment counter
        cache.set(cache_key, current_requests + 1, 60)  # 1 minute window
        return True
