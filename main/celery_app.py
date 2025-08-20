import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')

app = Celery('main')

# Load settingd from Django config with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
    "warmup-products-cache-every-5-min": {
        "task": "yourapp.tasks.warmup_product_cache",
        "schedule": 300.0,  # every 5 minutes
    },
}

# Discover tasks.py in all installed apps
app.autodiscover_tasks()