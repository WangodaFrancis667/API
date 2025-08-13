from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.utils import timezone
from decimal import Decimal

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

    email = models.EmailField(unique=True)
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

    objects = UserManager()

    # creating indexes for faster lookups
    class Meta:
        indexes = [
            models.Index(fields=['role']),  # Fast lookups by role
            models.Index(fields=['username']),
            models.Index(fields=['email']),  # Fast email lookups
            models.Index(fields=['phone']),  # Fast phone lookups
            models.Index(fields=['status']),  # Fast status filtering
            models.Index(fields=['wallet']),  # Fast wallet queries
            models.Index(fields=['role', 'status']),  # Composite index for common filters
            models.Index(fields=['email_verified', 'phone_verified']),  # Verification status queries
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"
    
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
    
