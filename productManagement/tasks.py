from celery import shared_task
from django.core.cache import cache
from .models import Categories, Products, ProductMetaData
from .serializers import CategoriesSerializer, ProductsSerializer, ProductMetaDataSerializer
import time

@shared_task
def send_welcome_email(user_email):
    # Simulate heavy email task
    time.sleep(5)
    print(f"Email sent to {user_email}")
    return f"Sent to {user_email}"



@shared_task
def refresh_categories_cache():
    queryset = Categories.objects.filter(is_active=True)
    serializer = CategoriesSerializer(queryset, many=True)
    data = serializer.data
    cache.set("categories_list", data, timeout=60*10)  # cache for 10 min
    return f"Categories cache refreshed with {len(data)} items"

LIST_CACHE_KEY = "products_list"
CACHE_TIMEOUT = 60 * 10  # 10 minutes


@shared_task
def warmup_product_cache():
    """Rebuild the full list + detail product caches periodically."""
    queryset = Products.objects.filter(is_active=True)
    serializer = ProductsSerializer(queryset, many=True)

    # Warm up list cache
    cache.set(LIST_CACHE_KEY, serializer.data, timeout=CACHE_TIMEOUT)

    # Warm up detail caches
    for product in queryset:
        detail_key = f"product_{product.id}"
        detail_data = ProductsSerializer(product).data
        cache.set(detail_key, detail_data, timeout=CACHE_TIMEOUT)

    return f"Warmed up {queryset.count()} products"


# product meta data caches
@shared_task
def warmup_productmetadata_cache():
    """Rebuild the full list + detail product caches periodically."""
    queryset = ProductMetaData.objects.filter(is_active=True)
    serializer = ProductMetaDataSerializer(queryset, many=True)

    # Warm up list cache
    cache.set(LIST_CACHE_KEY, serializer.data, timeout=CACHE_TIMEOUT)

    # Warm up detail caches
    for product in queryset:
        detail_key = f"product_{product.id}"
        detail_data = ProductsSerializer(product).data
        cache.set(detail_key, detail_data, timeout=CACHE_TIMEOUT)

    return f"Warmed up {queryset.count()} products"

