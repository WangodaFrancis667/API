from celery import shared_task
from django.core.cache import cache
from .models import Categories
from .serializers import CategoriesSerializer
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
