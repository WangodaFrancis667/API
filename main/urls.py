"""
URL configuration for main project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from APIHealth.views import health_check

urlpatterns = [

    # Server root page view
    path('', include('home_page.urls')),
    
    path('admin/', admin.site.urls),

    # Health check
    path('health/', health_check, name='health-check'),

    # authentication
    path('api/auth/', include('accounts.urls')),

    # products
    path('api/products/', include('productManagement.urls')),

    # app settings
    path('api/app/', include('app_settings.urls')),

    # notifications
    path('api/notifications/', include('notifications.urls')),

    # orders
    path("api/orders/", include("orders.urls")),
    
    # App Versioning and force updates
    path("api/updates/", include("force_update.urls")),
    
    # Earnings endpoints
    path("api/earnings/", include("earnings.urls")),

    # Add this line for DRF browsable API login/logout
    # path('api-auth/', include('rest_framework.urls')),
]
