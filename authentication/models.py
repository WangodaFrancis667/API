from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager

ROLES_DATA = (
    ('admin', 'Admin'),
    ('vendor', 'Vendor'),
    ('buyer', 'Buyer')
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


# Create your models here.
class User(AbstractUser):
    """
    User model representing application users with roles and profile information.
    Fields:
        email (EmailField): Unique email address for the user.
        role (CharField): User's role in the system, restricted to predefined choices (ROLES_DATA).
        profile_image (ImageField): Optional profile image, stored in 'profiles/' directory.
        phone (CharField): Optional phone number, indexed for fast lookup.
    Meta:
        indexes: 
            - Index on 'role' for efficient role-based queries.
            - Index on 'username' for fast username lookups (ensure 'username' field exists).
    Methods:
        __str__: Returns a string representation of the user, showing username and role.
    """
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLES_DATA, db_index=True)

    # Additional fields
    profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True, null=True, db_index=True)
    location = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    business_type = models.CharField(max_length=15, blank=True, null=True, db_index=True)

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=['role']), # Fast lookups by role
            models.Index(fields=['username'])
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"
    
"""
   Profiles are one-to-one so you keep the big User table clean and avoid sparse columns.
   Indexes on role and phone_number make filtering fast for API endpoints.
"""


# Creating profiles for the specific roles
class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')

    def __str__(self):
        return f"AdminProfile: {self.user.username}"


# Vendor profile
class VendorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile')
    location = models.CharField(max_length=50)
    business_type = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Vendor: {self.user.username} {self.business_type}"

class BuyerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer_profile')
    delivery_address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Buyer: {self.user.username}"