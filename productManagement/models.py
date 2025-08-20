from django.db import models
from django.conf import settings
from decimal import Decimal

User = settings.AUTH_USER_MODEL


# These are the categories displayed under categories on the app
class Categories(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=255)
    image_url = models.ImageField(max_length=255)
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
      null=False,
      blank=False
      )
  
  name = models.CharField(max_length=100) 
  display_name = models.CharField(max_length=100, null=True)
  description = models.TextField(max_length=500,null=True)
  category_type = models.CharField(max_length=50, null=True)
  is_active = models.IntegerField(default=1)
  sort_order = models.IntegerField(default=0) 
  created_at = models.DateTimeField(auto_now_add=True) 
  updated_at = models.DateTimeField(auto_now=True) 

# # products table
# class Products(models.Model):
#     vendor_id = models.IntegerField() 
#     photo = models.CharField(max_length=255) 
#     title = models.CharField(max_length=255)
#     description = models.TextField(max_length=500)

#     regular_price = models.DecimalField(
#         max_digits=12, 
#         decimal_places=2,
#         default=Decimal('0.00'), 
#         db_index=True
#     )

#     group_price = models.DecimalField(
#         max_digits=12, 
#         decimal_places=2,
#         default=Decimal('0.00'), 
#         db_index=True
#     )

#     min_quantity = models.IntegerField() 
#     unit = models.CharField(max_length=255)
#     category = models.CharField(max_length=255)
#     # is_multiple_images = models. tinyint(1) DEFAULT 0,
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     created_by_admin = models.ForeignKey(User, models.CASCADE) 


#  `photo`,  `unit`, `category`, `is_multiple_images`, `created_at`, `updated_at`, `created_by_admin`)
class Products(models.Model):
    vendor_id = models.ForeignKey(User, on_delete=models.CASCADE)  
    title = models.CharField(max_length=255)
    description = models.TextField(max_length=1000)
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
        related_name="products"
    )

    # created_by_admin = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['title', 'title']),
            # models.Index(fields=['user', 'verified']),
        ]

        verbose_name = "title"
       

    
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

