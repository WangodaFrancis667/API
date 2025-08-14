"""
Security utilities and helper functions for authentication and authorization.
"""
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import UserActivityLog
import logging
import hashlib
import secrets

User = get_user_model()
logger = logging.getLogger('accounts.security')


def log_user_activity(user, action, description, request=None, metadata=None):
    """
    Log user activity for audit purposes.
    """
    try:
        ip_address = None
        user_agent = None
        
        if request:
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        UserActivityLog.objects.create(
            user=user,
            action=action,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )
        
        # Also log to file
        logger.info(f"Activity: {user.username} - {action} - {description} - IP: {ip_address}")
        
    except Exception as e:
        logger.error(f"Failed to log user activity: {e}")


def generate_cache_key(prefix, user_id, suffix=''):
    """
    Generate a standardized cache key.
    """
    key = f"afrobuy:{prefix}:{user_id}"
    if suffix:
        key += f":{suffix}"
    return key


def cache_user_permissions(user):
    """
    Cache user permissions for faster access.
    """
    cache_key = generate_cache_key('permissions', user.id)
    
    permissions = {
        'role': user.role,
        'is_admin': user.role == 'admin',
        'is_vendor': user.role == 'vendor',
        'is_buyer': user.role == 'buyer',
        'is_verified': user.email_verified and user.phone_verified,
        'is_active': user.is_active and user.status == 'active',
        'can_make_purchases': user.role in ['buyer', 'admin'] and user.status == 'active',
        'can_sell': user.role in ['vendor', 'admin'] and user.status == 'active'
    }
    
    # Add vendor-specific permissions
    if user.role == 'vendor':
        try:
            vendor_profile = user.vendor_profile
            permissions.update({
                'is_verified_vendor': vendor_profile.is_verified_vendor,
                'can_receive_payments': vendor_profile.is_verified_vendor,
                'commission_rate': float(vendor_profile.commission_rate)
            })
        except:
            permissions.update({
                'is_verified_vendor': False,
                'can_receive_payments': False,
                'commission_rate': 0.0
            })
    
    cache.set(cache_key, permissions, 300)  # Cache for 5 minutes
    return permissions


def get_cached_user_permissions(user):
    """
    Get user permissions from cache or generate them.
    """
    cache_key = generate_cache_key('permissions', user.id)
    permissions = cache.get(cache_key)
    
    if permissions is None:
        permissions = cache_user_permissions(user)
    
    return permissions


def invalidate_user_cache(user_id):
    """
    Invalidate all cached data for a user.
    """
    cache_keys = [
        generate_cache_key('permissions', user_id),
        generate_cache_key('profile', user_id),
        f"vendor_verified_{user_id}",
        f"user_profile_{user_id}"
    ]
    
    cache.delete_many(cache_keys)
    logger.info(f"Cache invalidated for user {user_id}")


def check_rate_limit(key, limit, window=60):
    """
    Check if a rate limit has been exceeded.
    """
    current = cache.get(key, 0)
    if current >= limit:
        return False
    
    cache.set(key, current + 1, window)
    return True


def is_suspicious_activity(user, request):
    """
    Check for suspicious activity patterns.
    """
    # Get client IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    suspicious_indicators = []
    
    # Check for multiple accounts from same IP
    ip_cache_key = f"ip_users:{ip}"
    ip_users = cache.get(ip_cache_key, set())
    ip_users.add(user.username)
    
    if len(ip_users) > 5:  # More than 5 different users from same IP
        suspicious_indicators.append('multiple_users_same_ip')
    
    cache.set(ip_cache_key, ip_users, 3600)  # Cache for 1 hour
    
    # Check for rapid successive logins
    login_cache_key = f"rapid_login:{user.id}"
    login_count = cache.get(login_cache_key, 0)
    
    if login_count > 3:  # More than 3 logins in 5 minutes
        suspicious_indicators.append('rapid_logins')
    
    cache.set(login_cache_key, login_count + 1, 300)  # 5 minutes
    
    # Check user agent
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    if not user_agent or len(user_agent) < 10:
        suspicious_indicators.append('suspicious_user_agent')
    
    if suspicious_indicators:
        logger.warning(f"Suspicious activity detected for {user.username}: {suspicious_indicators}")
        log_user_activity(
            user, 
            'SUSPICIOUS_ACTIVITY', 
            f"Suspicious indicators: {', '.join(suspicious_indicators)}",
            request,
            {'indicators': suspicious_indicators}
        )
    
    return len(suspicious_indicators) > 0


def secure_hash(data):
    """
    Generate a secure hash for sensitive data.
    """
    salt = secrets.token_hex(16)
    return hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000).hex() + ':' + salt


def verify_secure_hash(data, hashed):
    """
    Verify a secure hash.
    """
    try:
        hash_part, salt = hashed.split(':')
        return hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000).hex() == hash_part
    except:
        return False


class SecurityMiddleware:
    """
    Custom security middleware for additional protection.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response


def clean_and_validate_input(data, field_rules):
    """
    Clean and validate input data based on field rules.
    """
    cleaned_data = {}
    
    for field, value in data.items():
        if field in field_rules:
            rule = field_rules[field]
            
            # Strip whitespace
            if isinstance(value, str):
                value = value.strip()
            
            # Apply field-specific cleaning
            if rule.get('type') == 'email':
                value = value.lower()
            elif rule.get('type') == 'phone':
                value = ''.join(filter(str.isdigit, value))
                if value.startswith('0'):
                    value = '+256' + value[1:]  # Convert to international format for Uganda
            
            # Length validation
            if 'max_length' in rule and len(str(value)) > rule['max_length']:
                raise ValueError(f"{field} exceeds maximum length of {rule['max_length']}")
            
            if 'min_length' in rule and len(str(value)) < rule['min_length']:
                raise ValueError(f"{field} must be at least {rule['min_length']} characters")
            
            cleaned_data[field] = value
    
    return cleaned_data


def get_user_dashboard_url(user):
    """
    Get the appropriate dashboard URL based on user role.
    """
    dashboard_urls = {
        'admin': '/admin/dashboard/',
        'vendor': '/vendor/dashboard/',
        'buyer': '/buyer/dashboard/'
    }
    
    return dashboard_urls.get(user.role, '/dashboard/')


def check_user_permissions(user, required_permissions):
    """
    Check if user has required permissions.
    """
    user_permissions = get_cached_user_permissions(user)
    
    for permission in required_permissions:
        if not user_permissions.get(permission, False):
            return False
    
    return True
