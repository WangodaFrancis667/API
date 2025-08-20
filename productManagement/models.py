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

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="categories_created",
        limit_choices_to={'role': 'admin'},
        db_column='created_by_id'
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def created_by_name(self):
        return self.created_by.username if self.created_by else "System"


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

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_metadata_created",
        limit_choices_to={'role': 'admin'},
        db_column='created_by_id'
    )
  
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True) 

    class Meta:
        verbose_name_plural = "Product MetaData"
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.get_type_display()}: {self.name}"

    def created_by_name(self):
        return self.created_by.username if self.created_by else "System"


# Product model
class Products(models.Model):
    vendor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="products_as_vendor",
       limit_choices_to={'role': 'vendor'},
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

    category = models.ForeignKey(
        Categories,
        on_delete=models.CASCADE,
        db_column='category_id'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products_created",
        limit_choices_to={'role__in': ['admin', 'vendor']},
        db_column='created_by_id'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'productManagement_products'
        verbose_name_plural = "Products"
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['category']),
            models.Index(fields=['vendor']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.category.name}"

    def category_name(self):
        return self.category.name

    def vendor_name(self):
        return self.vendor.username if self.vendor else "Unknown"

    def created_by_name(self):
        return self.created_by.username if self.created_by else "System"


# Product image
class ProductImage(models.Model):
    product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image_url = models.CharField(max_length=255)  # store "uploads/products/xyz.png"
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_images_created",
        limit_choices_to={'role': 'admin'},
        db_column='created_by_id'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Product Images"
        ordering = ['product', '-created_at']

    def __str__(self):
        return f"Image for {self.product.title}"

    def created_by_name(self):
        return self.created_by.username if self.created_by else "System"
    
