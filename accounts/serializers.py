from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from .models import User, AdminProfile, BuyerProfile, VendorProfile, UserActivityLog
import re
import logging

logger = logging.getLogger('accounts.security')


# User Registration serializer
class UserRegistrationSerializer(serializers.ModelSerializer):
    """
       Serializer for user registration
    """
    full_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    location = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'phone', 'location', 'password', 'role'
        ]

        extra_kwargs = {
            'email': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }
    
    def validate_email(self, value):
        # Validat eemail format and uniqueness
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError('A user with this email already exists')
        return value.lower()
    
    def validate_username(self, value):
        # validate username format
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise serializers.ValidationError('Username can only contain letters, numbers, and underscores')
        if len(value) < 4:
            raise serializers.ValidationError('Username must be atleast four characters long')
        return value
    
    def validate_phone(self, value):
        # validate and clean the phone
        if value:
            # remove spaces and special characters
            phone_clean = re.sub(r'[^\d+]', '', value)
            if not re.match(r'^\+?[1-9]\d{8,14}$', phone_clean):
                raise serializers.ValidationError('Please enter a valid phone number')
            return phone_clean
        return value
    
    def validate_role(self, value):
        # validate role assignment
        # Only allow buyer registration via public endpoint
        # Vendors must be created by admins
        if value not in ['buyer']:
            raise serializers.ValidationError('You can only register as a buyer. Vendor accounts are created by administrators.')
        return value
    
    def validate(self, attrs):
        # Check if the passwords are matching before confirming
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError('The passwords donont match')
        
        # remove password confirmation from the validated data
        attrs.pop['confirm_password']
        return attrs
    
    def create(self, validated_data):
        # create user with encrypted data and default profile
        user = User.objects.create_user(**validated_data)

        # create profile based on the user
        if User.role == 'buyer':
            BuyerProfile.objects.create(user=user)

            # Log Buyer registration
            logger.info(f"New user registered: {user.username} ({user.role})")
        
        elif User.role == 'admin':
            AdminProfile.objects.create(user=user)

            # Log Admin registration
            logger.info(f"New user registered: {user.username} ({user.role})")

        else:
            raise serializers.ValidationError('Role is not allowed via this endpoint, contact admins for help')

        return user


class VendorRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for vendor registration by admins only.
    """

    full_name = serializers.CharField(max_length=100)
    business_type = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=100)
    location = serializers.CharField(max_length=100)
    business_registration_number = serializers.CharField(max_length=50, required=False)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'full_name', 'phone', 'business_type', 'business_name'
             'location', 'password', 'confirm_password'
        )
        extra_kwargs = {
            'email': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'business_name': {'required': False},
        }

    def validate_email(self, value):
        """Validate email format and uniqueness."""
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()
    
    def validate_username(self, value):
        # validate username format
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise serializers.ValidationError('Username can only contain letters, numbers, and underscores')
        if len(value) < 4:
            raise serializers.ValidationError('Username must be atleast four characters long')
        return value
    
    def validate_phone(self, value):
        # validate and clean the phone
        if value:
            # remove spaces and special characters
            phone_clean = re.sub(r'[^\d+]', '', value)
            if not re.match(r'^\+?[1-9]\d{8,14}$', phone_clean):
                raise serializers.ValidationError('Please enter a valid phone number')
            return phone_clean
        return value
    
    def create(self, validated_data):
        """
           Create vendor with profile
        """
        # Extract vendor-specific fields
        business_type = validated_data.pop('business_type')
        business_registration_number = validated_data.pop('business_registration_number', '')

         # Set role to vendor
        validated_data['role'] = 'vendor'
        validated_data['status'] = 'pending'  # Vendors start as pending verification

        user = User.objects.create_user(**validated_data)

        # Create vendor profile
        VendorProfile.objects.create(
            user=user,
            business_type=business_type,
            business_registration_number=business_registration_number,
            is_verified_vendor=False
        )

        logger.info(f"New vendor created by admin: {user.username}")

        return user
    


class UserLoginSerializer(serializers.ModelSerializer):
    """
    Serializer for user login with security checks.
    """
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone = attrs.get('phone')
        password = attrs.get('password')

        if not phone or not password:
            raise serializers.ValidationError('phone and password are required')
        
        # try to get user by phone or email
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials.")
        
        # Check if account is locked
        if user.is_account_locked():
            raise serializers.ValidationError("Account is temporarily locked due to multiple failed login attempts.")
        
        # Check ccount status
        if user.status != 'active':
            raise serializers.ValidationError(f"Account is {user.status}. Please contact administrator.")
        
        # Authenticate
        user = authenticate(phone=phone, password=password)
        if not user:
            # Increment failed login attempts
            self._handle_failed_login(phone)
            raise serializers.ValidationError("Invalid credentials.")

        # Reset login attemots after a successfull login
        if user.login_attempts > 0:
            user.login_attempts = 0
            user.save(update_fields=['login_attempts'])

        attrs['user'] = user
        return attrs
    
    def _handle_failed_login(self, phone):
        """Handle failed login attempts with account locking."""

        try:
            user = User.objects.get(phone=phone)
            user.login_attempts += 1
            
            # Lock account after 5 failed attempts
            if user.login_attempts >= 5:
                user.lock_account(duration_minutes=30)
                logger.warning(f"Account locked for user: {phone}")
            
            user.save(update_fields=['login_attempts'])
            
        except User.DoesNotExist:
            pass  # Don't reveal if username exists


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile with role-specific information.
    """
    profile_data = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'full_name', 'email', 'first_name', 'last_name', 
            'phone', 'location', 'business_name', 'role', 'status',
            'wallet', 'referral_points', 'email_verified', 'phone_verified',
            'profile_image', 'date_joined', 'profile_data'
        )
        read_only_fields = ('id', 'full_name', 'role', 'wallet', 'referral_points', 'date_joined')

    def get_profile_data(self, obj):
        """Get role-specific profile data."""
        cache_key = f"user_profile_{obj.id}"
        profile_data = cache.get(cache_key)
        
        if profile_data is None:
            try:
                if obj.role == 'admin':
                    profile = obj.admin_profile
                    profile_data = {
                        'department': profile.department,
                        'permissions': profile.permissions
                    }
                elif obj.role == 'vendor':
                    profile = obj.vendor_profile
                    profile_data = {
                        'business_type': profile.business_type,
                        'commission_rate': str(profile.commission_rate),
                        'is_verified_vendor': profile.is_verified_vendor,
                        'business_registration_number': profile.business_registration_number
                    }
                elif obj.role == 'buyer':
                    profile = obj.buyer_profile
                    profile_data = {
                        'loyalty_tier': profile.loyalty_tier,
                        'delivery_address': profile.delivery_address,
                        'secondary_phone': profile.secondary_phone
                    }
                else:
                    profile_data = {}
                
                cache.set(cache_key, profile_data, 300)  # Cache for 5 minutes
            except:
                profile_data = {}
        
        return profile_data
    
    def validate_email(self, value):
        """Validate email uniqueness excluding current user."""
        if User.objects.filter(email=value.lower()).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()
    
    def update(self, instance, validated_data):
        """Update user profile with cache invalidation."""
        # Invalidate cache
        cache_key = f"user_profile_{instance.id}"
        cache.delete(cache_key)
        
        return super().update(instance, validated_data)
    
class PasswordChangeSerializer(serializers.ModelSerializer):
    """
    Serializer for password change with validation.
    """

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        """Validate old password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
    
    def validate(self, attrs):
        """Cross-field validation."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "New passwords don't match."})
        return attrs
    
    
    def save(self):
        """Change user password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        
        # Log password change
        logger.info(f"Password changed for user: {user.username}")
        
        return user
    
class AdminUserManagementSerializer(serializers.ModelSerializer):
    """
    Serializer for admin user management operations.
    """
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 
            'phone', 'location', 'business_name', 'role', 'status',
            'wallet', 'referral_points', 'email_verified', 'phone_verified',
            'is_active', 'login_attempts', 'account_locked_until'
        )
        read_only_fields = ('id', 'username', 'wallet', 'referral_points')
    
    def validate_role(self, value):
        """Validate role changes."""
        if self.instance and self.instance.role != value:

            # Log role changes
            logger.warning(f"Role change attempted: {self.instance.username} from {self.instance.role} to {value}")
        return value
    

class UserActivityLogSerializer(serializers.ModelSerializer):
    """
    Serializer for user activity logs.
    """
    user_display = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserActivityLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at')