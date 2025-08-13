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