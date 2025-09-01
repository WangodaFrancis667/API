from django.db import models, transaction
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.utils import timezone
from django.conf import settings

from decimal import Decimal
from datetime import timedelta

import random
import string
import secrets


# User roles
ROLES_DATA = (
    ('admin', 'Admin'),
    ('vendor', 'Vendor'),
    ('buyer', 'Buyer')
)

# status
STATUS_CHOICES = (
    ('active', 'Active'),
    ('inactive', 'Inactive'),
    ('suspended', 'Suspended'),
    ('pending', 'Pending'),
)


# Password reste model
class PasswordReset(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email = models.EmailField()
    verification_code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def create_fresh(cls, user, email, validity_minutes=15):
        """Create a fresh password reset code."""
        # Invalidate any existing codes
        cls.objects.filter(user=user, email=email, is_used=False).update(is_used=True)
        
        # Generate new code
        code = ''.join(random.choices(string.digits, k=6))
        expires_at = timezone.now() + timezone.timedelta(minutes=validity_minutes)
        
        return cls.objects.create(
            user=user,
            email=email,
            verification_code=code,
            expires_at=expires_at
        )
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        return not self.is_used and not self.is_expired()
    
    def __str__(self):
        return f"Password Reset for {self.user.username} - {self.verification_code}"


# email verification model
class EmailVerification(models.Model):
    USER_TYPES = (
        ('buyer', 'Buyer'),
        ('vendor', 'Vendor'),
        ('admin', 'Admin'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='email_verifications'
    )

    user_type = models.CharField(max_length=10, choices=USER_TYPES, db_index=True)
    email = models.EmailField(max_length=255, db_index=True)
    verification_code = models.CharField(max_length=6, db_index=True)
    expires_at = models.DateTimeField()
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['email', 'verification_code']),
            models.Index(fields=['user', 'verified']),
        ]

        constraints = [
            # Only one active (unverified, not expired) code per user + email
            models.UniqueConstraint(
                fields=['user', 'email', 'verified'],
                name='uniq_active_verification_per_user_email',
                condition=models.Q(verified=False),
            )
        ]

        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"
    
    def __str__(self):
        return f"{self.email} ({'Verified' if self.verified else 'Pending'})"
    
    @staticmethod
    def generate_code() -> str:
        # Generating a six digit code
        return f"{secrets.randbelow(999999):06}"
    
    @classmethod
    def create_fresh(cls, *, user, email, user_type, validity_minutes=10):
        # create a fresh verification, expires any previous then creates a new one
        with transaction.atomic():
            cls.objects.filter(user=user, email=email, verified=False).update(
                expires_at=timezone.now() - timedelta(seconds=1)
            )
            return cls.objects.create(
                user=user,
                email=email,
                user_type=user_type,
                verification_code=cls.generate_code(),
                expires_at=timezone.now() + timedelta(minutes=validity_minutes),
            )
        
    
    def mark_verified(self):
        # Mark email as verified and update the user's email status

        if self.verified:
            return
        
        self.verified = True
        self.verified_at = timezone.now()
        self.save(update_fields=['verified', 'verified_at'])

        # Flip user flag
        self.user.email_verified = True

        # persist the verified address on the user if that's your policy:
        if not self.user.email:
            self.user.email = self.email
        self.user.save(update_fields=['email_verified', 'email'])

        # Update the user model
        # self.user.email_verified = True
        # self.user.save(update_fields=['email_verified'])


# User management model
class UserManager(DjangoUserManager):
    """
    Custom manager for the User model, extending Django's built-in UserManager.
    Provides convenience methods for querying users by their role:
    - admins(): Returns a queryset of users with the 'admin' role.
    - vendors(): Returns a queryset of users with the 'vendor' role.
    - buyers(): Returns a queryset of users with the 'buyer' role.
    These methods help to easily filter users based on their assigned role, 
    improving code readability and maintainability when working with different user types.
    """

    def admins(self):
        return self.get_queryset().filter(role='admin')
    
    def vendors(self):
        return self.get_queryset().filter(role='vendor')
    
    def buyers(self):
        return self.get_queryset().filter(role='buyer')
    

# The user model
class User(AbstractUser):
    """
    Enhanced User model representing application users with roles, financial tracking, and security features.
    
    Fields:
        email (EmailField): Unique email address for the user.
        role (CharField): User's role in the system, restricted to predefined choices (ROLES_DATA).
        profile_image (ImageField): Optional profile image, stored in 'profiles/' directory.
        phone (CharField): Phone number, indexed for fast lookup and verification.
        location (CharField): User's location/address.
        business_name (CharField): Business name for vendors/admin users.
        
        # Financial fields (aligned with SQL schema)
        wallet (DecimalField): User's wallet balance for transactions.
        referral_points (IntegerField): Points earned through referrals.
        
        # Security and verification fields
        status (CharField): Account status (active, inactive, suspended, pending).
        email_verified (BooleanField): Whether email has been verified.
        phone_verified (BooleanField): Whether phone has been verified.
        login_attempts (IntegerField): Number of failed login attempts.
        account_locked_until (DateTimeField): Account lockout expiration.
        
    Meta:
        indexes: Optimized indexes for common query patterns.
        
    Methods:
        __str__: Returns a string representation of the user.
        is_account_locked: Checks if account is currently locked.
        lock_account: Locks the account for specified duration.
        unlock_account: Unlocks the account.
        add_wallet_balance: Safely adds to wallet balance.
        deduct_wallet_balance: Safely deducts from wallet balance (with validation).
    """

    # Adding the full name field
    full_name = models.CharField(max_length=255, blank=True)

    # Make first_name and last_name optional since we're not using them
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)

    email = models.EmailField(unique=True, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLES_DATA, db_index=True)

    # Enhanced profile fields
    profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    location = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    business_name = models.CharField(max_length=255, blank=True, null=True)

    # Financial Fields
    wallet = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'), 
        db_index=True
    )

    referral_points = models.IntegerField(default=0, db_index=True)

    # Security and verification fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)

    # Date and time objects
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    # creating indexes for faster lookups
    class Meta:
        indexes = [
            models.Index(name='idx_user_role', fields=['role']),  # Fast lookups by role
            models.Index(name='idx_user_username', fields=['username']),
            models.Index(name='idx_user_email', fields=['email']),  # Fast email lookups
            models.Index(name='idx_user_phone', fields=['phone']),  # Fast phone lookups
            models.Index(name='idx_user_status', fields=['status']),  # Fast status filtering
            models.Index(name='idx_user_wallet', fields=['wallet']),  # Fast wallet queries
            models.Index(name='idx_user_role_status', fields=['role', 'status']),  # Composite index for common filters
            models.Index(name='idx_user_username_role', fields=['username', 'role']),  # Fast vendor username lookups
            models.Index(name='idx_user_verification', fields=['email_verified', 'phone_verified']),  # Verification status queries
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"
    
    def save(self, *args, **kwargs):
        # Clear first name and last name if full_name is provided
        if self.email == '':
            self.email = None
            
        if self.full_name:
            self.first_name = ""
            self.last_name = ""
        super().save(*args, **kwargs)
    
    def is_account_locked(self):
        # Check if the account is currently locked
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False
    
    def lock_account(self, duration_minutes=30):
        # Lock account for a specified durations
        self.account_locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        self.save(update_fields=['account_locked_until'])

    def unlock_account(self):
        self.account_locked_until = None
        self.login_attempts = 0
        self.save(update_fields=['account_locked_until', 'login_attempts'])

    def add_wallet_balance(self, amount):
        # safely add to wallet balance
        if amount > 0:
            self.wallet += Decimal(str(amount))
            self.save(update_fields=['wallet'])
            return True
        return False
    

# Creating enhanced profiles for the specific roles
# Admin profile
class AdminProfile(models.Model):
    """
    Extended profile for admin users with admin-specific functionality.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    permissions = models.JSONField(default=dict, blank=True)  # Store admin permissions
    department = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"AdminProfile: {self.user.username}"
    

# Creating profiles for specific users
class VendorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile')
    business_type = models.CharField(max_length=100, blank=True, null=True)
    business_registration_number = models.CharField(max_length=50, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    bank_account_info = models.JSONField(default=dict, blank=True)  # Store bank details securely
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    is_verified_vendor = models.BooleanField(default=False)
    verification_documents = models.JSONField(default=list, blank=True)  # Store document paths/info

    # Creating indexes for faster lookkups
    class Meta:
        indexes = [
            models.Index(name='idx_vendor_business_type', fields=['business_type']),
            models.Index(name='idx_vendor_verified', fields=['is_verified_vendor']),
        ]
    
    def __str__(self):
        return f"Vendor: {self.user.username} - {self.user.business_name}"
    

class BuyerProfile(models.Model):
    """
    Enhanced buyer profile with delivery and preference information.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer_profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    delivery_address = models.TextField(blank=True, null=True)
    secondary_phone = models.CharField(max_length=20, blank=True, null=True)
    delivery_instructions = models.TextField(blank=True, null=True)
    preferred_delivery_time = models.CharField(max_length=50, blank=True, null=True)
    loyalty_tier = models.CharField(
        max_length=20, 
        choices=[('bronze', 'Bronze'), ('silver', 'Silver'), ('gold', 'Gold'), ('platinum', 'Platinum')],
        default='bronze'
    )
    
    class Meta:
        indexes = [
            models.Index(name='idx_buyer_loyalty', fields=['loyalty_tier']),
        ]

    def __str__(self):
        return f"Buyer: {self.user.username}"
    

# Activity logging model
class UserActivityLog(models.Model):
    """
    Track user activities and system events for audit purposes.
    """
    ACTION_CHOICES = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('PROFILE_UPDATE', 'Profile Update'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('WALLET_CREDIT', 'Wallet Credit'),
        ('WALLET_DEBIT', 'Wallet Debit'),
        ('ORDER_PLACED', 'Order Placed'),
        ('ACCOUNT_LOCKED', 'Account Locked'),
        ('ACCOUNT_UNLOCKED', 'Account Unlocked'),
        ('EMAIL_VERIFIED', 'Email Verified'),
        ('PHONE_VERIFIED', 'Phone Verified'),
        ('OTHER', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(name='idx_activity_user_created', fields=['user', 'created_at']),
            models.Index(name='idx_activity_action_created', fields=['action', 'created_at']),
            models.Index(name='idx_activity_created', fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.created_at}"
    

# Archive user model for storing user information upon deleting it
class ArchiveUser(models.Model):
    """
    Stores data of deleted user accounts for record-keeping and analytics.
    
    This model preserves essential information about users who have deleted their accounts,
    helping with analytics, compliance, and understanding user churn.
    """

    original_user_id = models.IntegerField(db_index=True)
    username = models.CharField(max_length=250)
    email =  models.EmailField()
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone =  models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLES_DATA)

    # Deletion information
    deleted_at = models.DateTimeField(default=timezone.now)
    delete_reason = models.TextField(blank=True)

    # Optional: Additional data that may need to be preserved
    account_created_at = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(name='idx_archived_user_id', fields=['original_user_id']),
            models.Index(name='idx_archived_deleted_at', fields=['deleted_at']),
            models.Index(name='idx_archived_role', fields=['role']),
        ]
        verbose_name = "Archived User"
        verbose_name_plural = "Archived Users"

    def __str__(self):
        return f"Archived: {self.full_name} ({self.email})"