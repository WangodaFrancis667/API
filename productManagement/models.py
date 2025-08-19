from django.db import models
from accounts.models import User

from decimal import Decimal


# These are the categories displayed under categories on the app
class Categories(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=255)
    image_url = models.ImageField(max_length=255)
    is_active = models.BooleanField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# products table
class Products(models.Model):
    vendor_id = models.IntegerField() 
    photo = models.CharField(max_length=255) 
    title = models.CharField(max_length=255)
    description = models.TextField(max_length=500)

    regular_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'), 
        db_index=True
    )

    group_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'), 
        db_index=True
    )

    min_quantity = models.IntegerField() 
    unit = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    # is_multiple_images = models. tinyint(1) DEFAULT 0,
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_admin = models.ForeignKey(User, models.CASCADE) 


