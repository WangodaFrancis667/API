from django.db import models
from django.conf import settings
from decimal import Decimal

User = settings.AUTH_USER_MODEL


# These are the categories displayed under categories on the app
class Categories(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=255)
    image_url = models.CharField(max_length=255) 
    is_active = models.BooleanField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# Table with the product units
class ProductMetaData(models.Model):
  class TypeChoices(models.TextChoices):
      CATEGORY = 'category', 'Category'
      UNIT = 'unit', 'Unit'

  type = models.CharField(
      max_length=255, 
      choices=TypeChoices.choices,
      default=TypeChoices.CATEGORY,
      null=True,
      blank=False
      )
  
  name = models.CharField(max_length=100) 
  display_name = models.CharField(max_length=100, null=True)
  description = models.TextField(max_length=500,null=True)
  category_type = models.CharField(max_length=50, null=True)
  is_active = models.BooleanField(default=True)
  sort_order = models.IntegerField(default=0) 
  created_at = models.DateTimeField(auto_now_add=True) 
  updated_at = models.DateTimeField(auto_now=True) 

#  `photo`,  `unit`, `category`, `is_multiple_images`, `created_at`, `updated_at`, `created_by_admin`)
class Products(models.Model):
    vendor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="products_as_vendor",
        # limit_choices_to={'groups__name': 'Vendor'},
        db_column='vendor_id'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    regular_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        db_index=True
    )

    group_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        db_index=True
    )

    min_quantity = models.IntegerField()
    unit = models.CharField(max_length=255)

    # better to use ForeignKey to Categories table instead of CharField
    category = models.ForeignKey(
        Categories,
        on_delete=models.CASCADE,
        # related_name="products",
        # null=True, 
        # blank=True,
        db_column='category_id'
    )

    # created_by_admin = models.ForeignKey(
    #     User,
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name="products_created",
    #     limit_choices_to={'groups__name': 'Admin'},
    #     db_column='created_by_admin_id'
    # )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'productManagement_products'
        indexes = [
            models.Index(fields=['title']),
        ]
       
    
    def __str__(self):
        return self.title


class ProductImage(models.Model):
    product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image_url = models.CharField(max_length=255)  # store "uploads/products/xyz.png"

    def __str__(self):
        return f"Image for {self.product.title}"

