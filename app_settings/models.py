from django.db import models

# Create your models here.
class AppSettings(models.Model):
  setting_key = models.CharField(max_length=100, null=False)
  setting_value = models.TextField(null=False)
  created_at = models.DateTimeField(auto_now_add=True) 
  updated_at = models.DateTimeField(auto_now=True)
