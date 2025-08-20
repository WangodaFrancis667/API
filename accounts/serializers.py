from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache

from .models import (
    User, AdminProfile, BuyerProfile, VendorProfile,
    UserActivityLog, ArchiveUser, EmailVerification,
    PasswordReset,
)

import re
import logging


logger = logging.getLogger('accounts.security')


# Serializer for adding an email
class AddEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.email = self.validated_data['email'].lower()
        user.email_verified = False
        user.save(update_fields=['email', 'email_verified'])
        return user


# User Registration serializer
class UserRegistrationSerializer(serializers.Serializer):
    """
       Serializer for user registration
    """
    full_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    location = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

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
        attrs.pop('confirm_password')
        return attrs
    
    def create(self, validated_data):
        # create user with encrypted data and default profile

        # Generate username from phone if not provided
        if 'username' not in validated_data or not validated_data['username']:
            # use phone number as username ensuring uniqueness
            base_username = validated_data.get('phone')
            username = base_username

            # Check if username exists and make it unique if needed
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            validated_data['username'] = username

            # Ensure role is set to 'buyer' for public registration
            validated_data['role'] = 'buyer'

        # Create user with encrypted password
        password = validated_data.pop('password')
        user = User.objects.create_user(
            password=password,
            **validated_data
        )


        # create profile based on the user
        if user.role == 'buyer':  # Changed from User.role to user.role
            BuyerProfile.objects.create(
            user=user,
            phone=user.phone,
            full_name=user.full_name,
            location=user.location
            )
            logger.info(f"New user registered: {user.username} ({user.role})")

        elif user.role == 'admin':  # Changed from User.role to user.role
            AdminProfile.objects.create(user=user)

            # Log Admin registration
            logger.info(f"New user registered: {user.username} ({user.role})")

        else:
            raise serializers.ValidationError('Role is not allowed via this endpoint, contact admins for help')

        return user


class VendorRegistrationSerializer(serializers.Serializer):
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
    

class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login with security checks.
    """

    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if not username or not password:
            raise serializers.ValidationError('username and password are required')
        
        # try to get user by phone or email
        try:
            user = User.objects.get(username=username)

            # Check if the account is locked
            if user.is_account_locked():
                raise serializers.ValidationError("Account is temporarily locked due to multiple failed login attempts.")
            
            # Check account status
            if user.status != 'active':
                raise serializers.ValidationError(f"Account is {user.status}. Please contact administrator.")
        
            
            # Authenticate with phone and password
            authenticated_user = authenticate(username=username, password=password)
            if not authenticated_user:
                self._handle_failed_login(username)
                raise serializers.ValidationError("Invalid credentials.")
            
            # Reset login attempts after successful login
            if user.login_attempts > 0:
                user.login_attempts = 0
                user.save(update_fields=['login_attempts'])

            # Generate tokens
            refresh = RefreshToken.for_user(user)
    
            return {
                'user': {
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role,
                'phone': user.phone if user.phone else None,
                'location': user.location if user.location else None,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile_image': user.profile_image.url if user.profile_image else None,
                },
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }
        
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials.")
        
    
    def _handle_failed_login(self, username):
        """Handle failed login attempts with account locking."""

        try:
            user = User.objects.get(username=username)
            user.login_attempts += 1
            
            # Lock account after 5 failed attempts
            if user.login_attempts >= 5:
                user.lock_account(duration_minutes=30)
                logger.warning(f"Account locked for user: {username}")
            
            user.save(update_fields=['login_attempts'])
            
        except User.DoesNotExist:
            pass  # Don't reveal if username exists


class ProfileUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating user profile information, including role-specific profile details.
    Handles both User model fields and related profile model fields in a single update operation.
    """
    
    # common fileds
    full_name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    profile_image = serializers.ImageField(required=False)

    # Admin profile fields
    department = serializers.CharField(required=False, allow_blank=True)

    # Vendor profile fields
    business_type = serializers.CharField(required=False, allow_blank=True)
    business_registration_number = serializers.CharField(required=False, allow_blank=True)
    tax_id = serializers.CharField(required=False, allow_blank=True)
    bank_account_info = serializers.JSONField(required=False)

     # Buyer profile fields
    delivery_address = serializers.JSONField(required=False)
    secondary_phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            'full_name', 'email', 'phone', 'location', 'business_name', 'profile_image',

            # Admin fields
            'department',

            # Vendor fields
            'business_type', 'business_registration_number', 'tax_id', 'bank_account_info',

            # Buyer fields
            'delivery_address', 'secondary_phone',
        )

    def validate_email(self, value):
        """Validate email uniqueness excluding current user."""
        if User.objects.filter(email=value.lower()).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("A User with this email already exists!")
        
    
    def validate_phone(self, value):
        """Validate phone format and uniqueness."""
        if value:
            # Clean phone number
            phone_clean = re.sub(r'[^\d+]', '', value)
            if not re.match(r'^\+?[1-9]\d{8,14}$', phone_clean):
                raise serializers.ValidationError('Please enter a valid phone number')
            
            # Check uniqueness
            if User.objects.filter(phone=phone_clean).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError("A user with this phone number already exists.")
            
            return phone_clean
        return value
    
    def validate(self, attrs):
        # validate that only relevant profile fields are provided based on the user role
        user = self.instance
        role = user.role


        # Check admin fields
        admin_fields = ['department']
        if role != 'admin' and any(field in attrs for field in admin_fields):
            raise serializers.ValidationError("Admin profile fields can only be updated by admin users!")
        
        # Check vendorfields
        vendor_fields = ['business_type', 'business_registration_number', 'tax_id', 'bank_account_info']
        if role != 'vendor' and any(field in attrs for field in vendor_fields):
            raise serializers.ValidationError("Vendor profile fields can only be updated by vendors only!")
        
        # Check buyer fields
        buyer_fields = ['delivery_address', 'secondary_phone']
        if role != 'buyer' and any(field in attrs for field in buyer_fields):
            raise serializers.ValidationError("Buyer profile fields can only be updated by buyers only!")
        
        return attrs
    
    def update(self, instance, validated_data):
        """Update both user model and related profile model."""
        # Extract profile-specific data
        admin_data = {}
        vendor_data = {}
        buyer_data = {}

        # Admin profile fields
        if 'department' in validated_data:
             admin_data['department'] = validated_data.pop('department')

        # Vendor profile fields
        for field in ['business_type', 'business_registration_number', 'tax_id', 'bank_account_info']:
            if field in validated_data:
                vendor_data[field] = validated_data.pop(field)
        
        # Buyer profile fields
        for field in ['delivery_address', 'secondary_phone']:
            if field in validated_data:
                buyer_data[field] = validated_data.pop(field)

        # Update user model
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update role-specific profile
        if instance.role == 'admin' and admin_data and hasattr(instance, 'admin_profile'):
            admin_profile = instance.admin_profile
            for attr, value in admin_data.items():
                setattr(admin_profile, attr, value)
            admin_profile.save()
        
        elif instance.role == 'vendor' and vendor_data and hasattr(instance, 'vendor_profile'):
            vendor_profile = instance.vendor_profile
            for attr, value in vendor_data.items():
                setattr(vendor_profile, attr, value)
            vendor_profile.save()
        
        elif instance.role == 'buyer' and buyer_data and hasattr(instance, 'buyer_profile'):
            buyer_profile = instance.buyer_profile
            for attr, value in buyer_data.items():
                setattr(buyer_profile, attr, value)
            buyer_profile.save()     

        # Invalidate cache
        cache_key = f"user_profile_{instance.id}"
        cache.delete(cache_key)

        # Log profile update
        logger.info(f"Profile updated for user: {instance.username}")  

        return instance     

    
class UserProfileSerializer(serializers.Serializer):
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


class PasswordChangeSerializer(serializers.Serializer):
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
  
    
class AdminUserManagementSerializer(serializers.Serializer):
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
    

class UserActivityLogSerializer(serializers.Serializer):
    """
    Serializer for user activity logs.
    """
    user_display = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserActivityLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


# This enables users to delete their accounts
class UserDeleteSerializer(serializers.Serializer):
    """
    Serializer for account deletion with password confirmation.
    """
    password = serializers.CharField(write_only=True, required=True)
    delete_reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate_password(self, value):
        """Validate user's password before allowing account deletion."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Password is incorrect.")
        return value
    
    def save(self):
        """
        Handle the account deletion process.
        - Log the deletion
        - Archive user data if needed
        - Delete the user account
        """
        user = self.context['request'].user
        username = user.username
        user_id = user.id
        delete_reason = self.validated_data.get('delete_reason', '')
        
        # Log the account deletion
        logger.warning(f"Account deletion: User {username} (ID: {user_id}) - Reason: {delete_reason}")
        
        
        # Archive user date in the database
        ArchiveUser.objects.create(
            original_user_id=user.id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            full_name=user.full_name,
            role=user.role,
            deleted_at=timezone.now(),
            delete_reason=delete_reason,
            account_created_at=user.date_joined,
            last_login=user.last_login,
            wallet_balance=user.wallet
        )
        
        # Delete the user account
        user.delete()
        
        return {'success': True, 'message': 'Your account has been successfully deleted.'}
    

# Password reset request
class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting a password reset through email.
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        email = value.lower()
        if not User.objects.filter(email=email).exists():
            # Don't reveal if user exists for security
            pass
        return email
    
    # email_or_phone = serializers.CharField(required=True)
    
    # def validate(self, attrs):
    #     email_or_phone = attrs.get('email_or_phone')
        
    #     # Check if input is email or phone
    #     if '@' in email_or_phone:
    #         # Looks like an email
    #         if not User.objects.filter(email=email_or_phone.lower()).exists():
    #             # We don't reveal whether the email exists for security reasons
    #             # Just return without error and handle in view
    #             pass
    #         attrs['is_email'] = True
    #     else:
    #         # Looks like a phone number
    #         # Clean phone number
    #         phone_clean = re.sub(r'[^\d+]', '', email_or_phone)
    #         if not User.objects.filter(phone=phone_clean).exists():
    #             # We don't reveal whether the phone exists for security reasons
    #             # Just return without error and handle in view
    #             pass
    #         attrs['is_email'] = False
    #         attrs['email_or_phone'] = phone_clean
            
    #     return attrs


# Password Verification
class PasswordResetVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying a password reset token.
    """
    email = serializers.EmailField()
    verification_code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs['email'].lower()
        code = attrs['verification_code']

        try:
            user = User.objects.get(email=email)
            reset = PasswordReset.objects.filter(
                user=user,
                email=email,
                verification_code=code,
                is_used=False
            ).first()
            
            if not reset:
                raise serializers.ValidationError("Invalid verification code.")
            
            if reset.is_expired():
                raise serializers.ValidationError("Verification code has expired.")
            
            attrs['reset_instance'] = reset
            attrs['user'] = user
            
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email address.")
        
        return attrs

    # token = serializers.CharField(required=True)
    # uidb64 = serializers.CharField(required=True)


# Password reset confirmation
class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming a password reset with a new password.
    """
    email = serializers.EmailField()
    verification_code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        
        email = attrs['email'].lower()
        code = attrs['verification_code']
        
        try:
            user = User.objects.get(email=email)
            reset = PasswordReset.objects.filter(
                user=user,
                email=email,
                verification_code=code,
                is_used=False
            ).first()
            
            if not reset:
                raise serializers.ValidationError("Invalid verification code.")
            
            if reset.is_expired():
                raise serializers.ValidationError("Verification code has expired.")
            
            attrs['reset_instance'] = reset
            attrs['user'] = user
            
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email address.")
        
        return attrs
    
    def save(self):
        reset = self.validated_data['reset_instance']
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']
        
        # Update password
        user.set_password(new_password)
        
        # Reset account security
        user.login_attempts = 0
        if user.is_account_locked():
            user.unlock_account()
        
        user.save()
        
        # Mark reset as used
        reset.is_used = True
        reset.save()
        
        return user

    # token = serializers.CharField(required=True)
    # uidb64 = serializers.CharField(required=True)
    # new_password = serializers.CharField(write_only=True, validators=[validate_password])
    # new_password_confirm = serializers.CharField(write_only=True)
    
    # def validate(self, attrs):
    #     """Validate passwords match."""
    #     if attrs['new_password'] != attrs['new_password_confirm']:
    #         raise serializers.ValidationError({"new_password_confirm": "Passwords don't match."})
        
    #     # Token validation will be done in the view
    #     return attrs


# Email sending verification
class SendEmailVerificationSerializer(serializers.Serializer):
    """
    Serializer for sending email verification.

    Fields:
        email (EmailField): The email address to send the verification to.
        user_type (ChoiceField): The type of user, must be one of EmailVerification.USER_TYPES.

    Methods:
        create(validated_data):
            Creates an EmailVerification instance for the given user and email.
            Args:
                validated_data (dict): Validated data containing 'email' and 'user_type'.
            Returns:
                EmailVerification: The created verification instance.
    """
    email = serializers.EmailField()
    user_type = serializers.ChoiceField(choices=EmailVerification.USER_TYPES)

    def validate(self, attrs):
        request = self.context['request']
        user = request.user

        # Checking if the user has an attached email
        if not user.email:
            raise serializers.ValidationError("No email found. Please add one first.")
        
        # making sure the email and user match
        if user.email and user.email.lower() != attrs['email'].lower():
            raise serializers.ValidationError("Email doesn't match the one on file.")
        
        # Checking if the email is already verified
        if user.email_verified:
            raise serializers.ValidationError("Email already verified.")
        
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        email = validated_data['email'].lower()

        # Wrapping this under a transaction
        with transaction.atomic():
            # Deleting unverified or expired codes for the current user and email
            verification, created = EmailVerification.objects.update_or_create(
            user=user,
            email=email,
            verified=False,
            defaults={
                'user_type': validated_data['user_type'],
                'verification_code': EmailVerification.generate_code(),  # or however you generate it
                'expires_at': timezone.now() + timedelta(minutes=10),
            }
        )

        return verification
    

# Email confirmation 
class ConfirmEmailVerificationSerializer(serializers.Serializer):
    """
    Serializer for confirming email verification codes.

    Fields:
        email (EmailField): The email address to verify.
        verification_code (CharField): The verification code sent to the email.

    Methods:
        validate(attrs):
            Validates the provided email and verification code.
            - Checks if a matching, unverified EmailVerification exists.
            - Checks if the code has expired.
            - Adds the verification instance to attrs for use in save().
        save():
            Marks the verification as verified.
            Returns the verification instance.
    """
    email = serializers.EmailField()
    verification_code = serializers.CharField(min_length=6, max_length=6)

    def validate(self, attrs):
        email=attrs['email'].lower()
        code=attrs['verification_code']
        user = self.context['request'].user

        try:
            ver = (EmailVerification.objects
                   .select_for_update()
                   .get(user=user, email=email, verification_code=code, verified=False))
        except EmailVerification.DoesNotExist:
            raise serializers.ValidationError("Invalid code or email.")
        
        if ver.expires_at < timezone.now():
            raise serializers.ValidationError("Verification code has expired.")
        attrs['verification'] = ver
        return attrs
    
    def save(self, **kwargs):
        ver: EmailVerification = self.validated_data['verification']
        ver.mark_verified()
        return ver


