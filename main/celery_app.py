import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')

app = Celery('main')

# Load settingd from Django config with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover tasks.py in all installed apps
app.autodiscover_tasks()