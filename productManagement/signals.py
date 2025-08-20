# making sure your Redis cache is always up-to-date instantly whenever an admin adds/updates/deletes a category

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Categories, Products, ProductImage
from .serializers import CategoriesSerializer, ProductsSerializer

CACHE_KEY = "products_list"
LIST_CACHE_KEY = "products_list"
CACHE_TIMEOUT = 60 * 10  # 10 minutes (you can adjust)

def refresh_categories_cache():
    """Refresh categories list in Redis."""
    queryset = Categories.objects.filter(is_active=True)
    serializer = CategoriesSerializer(queryset, many=True)
    cache.set("categories_list", serializer.data, timeout=60*10)

@receiver(post_save, sender=Categories)
def update_cache_on_save(sender, instance, **kwargs):
    refresh_categories_cache()

@receiver(post_delete, sender=Categories)
def update_cache_on_delete(sender, instance, **kwargs):
    refresh_categories_cache()


def refresh_products_cache():
    """Refresh all products in Redis cache."""
    queryset = Products.objects.all().prefetch_related("images")
    serializer = ProductsSerializer(queryset, many=True)
    cache.set("products_list", serializer.data, timeout=60 * 10)


@receiver(post_save, sender=Products)
@receiver(post_delete, sender=Products)
@receiver(post_save, sender=ProductImage)
@receiver(post_delete, sender=ProductImage)
def update_cache_on_change(sender, instance, **kwargs):
    refresh_products_cache()


@receiver(post_save, sender=Products)
def clear_products_cache_on_save(sender, instance, **kwargs):
    """
    Clear products cache whenever a product is created or updated.
    Works for API, Django admin, or any other save.
    """
    cache.delete(CACHE_KEY)


@receiver(post_delete, sender=Products)
def clear_products_cache_on_delete(sender, instance, **kwargs):
    """
    Clear products cache whenever a product is deleted.
    Works for API, Django admin, or any other delete.
    """
    cache.delete(CACHE_KEY)


def rebuild_cache():
    """Fetch all active products, serialize them, and refresh Redis cache."""
    queryset = Products.objects.filter(is_active=True)
    serializer = ProductsSerializer(queryset, many=True)
    cache.set(CACHE_KEY, serializer.data, timeout=CACHE_TIMEOUT)


@receiver(post_save, sender=Products)
def refresh_cache_on_save(sender, instance, **kwargs):
    """
    Refresh cache whenever a product is created or updated.
    Works seamlessly for API, Django admin, and scripts.
    """
    rebuild_cache()


@receiver(post_delete, sender=Products)
def refresh_cache_on_delete(sender, instance, **kwargs):
    """
    Refresh cache whenever a product is deleted.
    """
    rebuild_cache()

def rebuild_list_cache():
    """Rebuild the full products list cache."""
    queryset = Products.objects.filter(is_active=True)
    serializer = ProductsSerializer(queryset, many=True)
    cache.set(LIST_CACHE_KEY, serializer.data, timeout=CACHE_TIMEOUT)


def rebuild_detail_cache(product):
    """Rebuild cache for a single product."""
    serializer = ProductsSerializer(product)
    cache.set(f"product_{product.id}", serializer.data, timeout=CACHE_TIMEOUT)


@receiver(post_save, sender=Products)
def refresh_cache_on_save(sender, instance, **kwargs):
    """Refresh both list + detail caches when a product is created/updated."""
    rebuild_list_cache()
    if instance.is_active:  # only cache active products
        rebuild_detail_cache(instance)
    else:
        cache.delete(f"product_{instance.id}")


@receiver(post_delete, sender=Products)
def refresh_cache_on_delete(sender, instance, **kwargs):
    """Refresh list cache + delete detail cache when a product is deleted."""
    rebuild_list_cache()
    cache.delete(f"product_{instance.id}")
