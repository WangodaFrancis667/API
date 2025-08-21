# API TESTING GUIDE - CURL COMMANDS OVERVIEW
# Django E-Commerce API - Complete Testing Suite
# Generated: August 21, 2025

# ===============================
# QUICK REFERENCE
# ===============================

# Base URLs:
# - Local Development: http://localhost:8000
# - Production: https://your-api-domain.com

# Authentication:
# - JWT Bearer Tokens required for most endpoints
# - Token format: Authorization: Bearer YOUR_ACCESS_TOKEN

# ===============================
# FILE ORGANIZATION
# ===============================

# This testing suite includes the following files:
# 1. accounts_curl.txt          - User authentication, profiles, admin functions
# 2. productManagement_curl.txt - Products, categories, images, metadata
# 3. app_settings_curl.txt      - Application configuration settings
# 4. notifications_curl.txt     - In-app notifications and messaging
# 5. orders_curl.txt            - Order management, payments, returns
# 6. general_curl.txt           - Health checks, system status, utilities
# 7. README_curl.txt            - This overview file

# ===============================
# GETTING STARTED
# ===============================

# 1. Start the Django development server:
python manage.py runserver

# 2. Test basic connectivity:
curl -X GET http://localhost:8000/health/

# 3. Create a test user account:
curl -X POST http://localhost:8000/api/auth/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User",
    "phone": "+1234567890",
    "location": "Test City",
    "password": "TestPass123!",
    "confirm_password": "TestPass123!"
  }'

# 4. Login to get access tokens:
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "1234567890",
    "password": "TestPass123!"
  }'

# 5. Use the access token for authenticated requests:
# Replace YOUR_ACCESS_TOKEN with the token from login response

# ===============================
# API STRUCTURE OVERVIEW
# ===============================

# ACCOUNTS APP (/api/auth/):
# - User registration and authentication
# - Profile management
# - Email verification and password reset
# - Admin user management
# - Activity logging and dashboard stats

# PRODUCT MANAGEMENT APP (/api/products/):
# - Product CRUD operations
# - Category management
# - Product metadata and units
# - Image upload and management
# - Vendor-specific product management

# APP SETTINGS APP (/api/app/):
# - Application configuration
# - Feature flags and system settings
# - Maintenance and deployment settings

# NOTIFICATIONS APP (/api/notifications/):
# - In-app notification system
# - OTP and verification codes
# - Order and system notifications
# - Notification preferences

# ORDERS APP (/api/orders/):
# - Order creation and management
# - Group order functionality
# - Payment processing
# - Order returns and refunds
# - Order tracking and analytics

# GENERAL ENDPOINTS (/):
# - Health checks and system status
# - API documentation
# - Cache management
# - Export and analytics

# ===============================
# USER ROLES & PERMISSIONS
# ===============================

# BUYER:
# - Can register via public signup
# - Can view products and place orders
# - Can manage their own profile and orders
# - Can request returns and track orders

# VENDOR:
# - Created by admins only
# - Can manage their own products
# - Can view and process their orders
# - Can handle returns for their products
# - Requires verification by admin

# ADMIN:
# - Full system access
# - Can manage all users, products, orders
# - Can create vendor accounts
# - Can access system analytics and settings
# - Can perform maintenance operations

# ===============================
# COMMON WORKFLOW EXAMPLES
# ===============================

# BUYER WORKFLOW:
# 1. Register account -> 2. Verify email -> 3. Browse products -> 
# 4. Place order -> 5. Make payment -> 6. Track order -> 7. Request return (if needed)

# VENDOR WORKFLOW:
# 1. Account created by admin -> 2. Get verified -> 3. Add products -> 
# 4. Upload product images -> 5. Process incoming orders -> 6. Update order status

# ADMIN WORKFLOW:
# 1. Monitor system health -> 2. Manage user accounts -> 3. Create vendors -> 
# 4. Configure app settings -> 5. Review analytics -> 6. Handle escalations

# ===============================
# TESTING CHECKLIST
# ===============================

# AUTHENTICATION & USERS:
# □ User registration (buyer)
# □ User login/logout
# □ Token refresh
# □ Profile update
# □ Email verification
# □ Password reset
# □ Admin user management
# □ Vendor creation and verification

# PRODUCTS & CATALOG:
# □ View categories
# □ Create/update/delete products
# □ Upload product images
# □ Manage product metadata
# □ Search and filter products
# □ Vendor-specific product management

# ORDERS & PAYMENTS:
# □ Create individual orders
# □ Create group orders
# □ Update order status
# □ Process payments
# □ Handle returns
# □ Order tracking
# □ Generate invoices

# NOTIFICATIONS:
# □ View notifications
# □ Mark as read/unread
# □ Create custom notifications
# □ OTP verification
# □ Notification preferences

# SYSTEM & ADMIN:
# □ Health checks
# □ App settings management
# □ Cache operations
# □ Export data
# □ Analytics and reporting
# □ Maintenance mode

# ===============================
# ERROR HANDLING PATTERNS
# ===============================

# Standard Error Response Format:
# {
#   "error": "Error type or message",
#   "details": {
#     "field_name": ["Specific error message"]
#   },
#   "code": "ERROR_CODE" (optional),
#   "timestamp": "2025-08-21T12:00:00Z" (optional)
# }

# Common HTTP Status Codes:
# 200 - OK (Success)
# 201 - Created
# 204 - No Content
# 400 - Bad Request (Validation errors)
# 401 - Unauthorized (Authentication required)
# 403 - Forbidden (Insufficient permissions)
# 404 - Not Found
# 409 - Conflict (Duplicate data)
# 422 - Unprocessable Entity (Business logic error)
# 429 - Too Many Requests (Rate limited)
# 500 - Internal Server Error

# ===============================
# RATE LIMITING
# ===============================

# Default Rate Limits:
# - Anonymous users: 100 requests/hour
# - Authenticated users: 1000 requests/hour
# - Login attempts: 5 per minute
# - Registration: 3 per minute

# Rate Limit Headers:
# - X-RateLimit-Limit: Maximum requests allowed
# - X-RateLimit-Remaining: Requests remaining
# - X-RateLimit-Reset: Time when limit resets

# ===============================
# ENVIRONMENT VARIABLES
# ===============================

# Required Environment Variables:
# - SECRET_KEY: Django secret key
# - DEBUG: Debug mode (True/False)
# - ALLOWED_HOSTS: Comma-separated allowed hosts
# - DATABASE_URL: Database connection string
# - REDIS_URL: Redis connection for cache/celery
# - EMAIL_* variables for email service
# - CORS_ALLOWED_ORIGINS: Frontend URLs

# ===============================
# PERFORMANCE CONSIDERATIONS
# ===============================

# Pagination:
# - Most list endpoints support limit/offset pagination
# - Default page size: 25 items
# - Use ?limit=X&offset=Y parameters

# Caching:
# - Categories and metadata are cached
# - User permissions are cached
# - Clear cache after administrative changes

# File Uploads:
# - Maximum file size: 5MB (configurable)
# - Supported formats: JPG, PNG, WebP
# - Images stored in /media/uploads/

# ===============================
# SECURITY BEST PRACTICES
# ===============================

# Authentication:
# - Always use HTTPS in production
# - Store JWT tokens securely (httpOnly cookies recommended)
# - Implement token rotation
# - Use strong passwords (enforced by validation)

# API Security:
# - Validate all input data
# - Implement CORS properly
# - Use CSRF protection where needed
# - Monitor for suspicious activity

# Data Protection:
# - Encrypt sensitive data at rest
# - Use proper database permissions
# - Implement audit logging
# - Regular security updates

# ===============================
# DEVELOPMENT TIPS
# ===============================

# Local Development:
# - Use python manage.py runserver for development
# - Enable DEBUG=True for detailed error messages
# - Use Django Admin at /admin/ for data inspection
# - Monitor logs for errors and performance

# Testing:
# - Use different user accounts for different roles
# - Test with realistic data volumes
# - Verify error handling and edge cases
# - Test rate limiting and security features

# Debugging:
# - Check Django logs for detailed errors
# - Use Django Debug Toolbar for performance
# - Monitor database queries for optimization
# - Use Redis CLI to inspect cache data

# ===============================
# PRODUCTION DEPLOYMENT
# ===============================

# Checklist for Production:
# □ Set DEBUG=False
# □ Configure proper ALLOWED_HOSTS
# □ Use production database (PostgreSQL recommended)
# □ Set up Redis for caching and Celery
# □ Configure email service
# □ Set up proper logging
# □ Configure static/media file serving
# □ Set up SSL/HTTPS
# □ Configure backup systems
# □ Set up monitoring and alerting

# ===============================
# SUPPORT & DOCUMENTATION
# ===============================

# Additional Resources:
# - Django Documentation: https://docs.djangoproject.com/
# - Django REST Framework: https://www.django-rest-framework.org/
# - JWT Documentation: https://django-rest-framework-simplejwt.readthedocs.io/
# - Redis Documentation: https://redis.io/documentation
# - Celery Documentation: https://docs.celeryproject.org/

# For Issues:
# 1. Check the Django logs first
# 2. Verify environment variables are set correctly
# 3. Ensure database migrations are up to date
# 4. Check Redis connection for cache/celery issues
# 5. Verify user permissions and authentication tokens

# ===============================
# VERSION INFORMATION
# ===============================

# API Version: 1.0.0
# Django Version: 5.2.5
# Python Version: 3.13+
# Database: PostgreSQL (recommended) / SQLite (development)
# Cache: Redis
# Task Queue: Celery
# Authentication: JWT (Simple JWT)

# Last Updated: August 21, 2025
# Generated by: GitHub Copilot Analysis

# ===============================
# QUICK COMMAND EXAMPLES
# ===============================

# Get system health:
curl -X GET http://localhost:8000/health/

# Login:
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_phone", "password": "your_password"}'

# Get user profile:
curl -X GET http://localhost:8000/api/auth/profile/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# List products:
curl -X GET http://localhost:8000/api/products/view-products/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create order:
curl -X POST http://localhost:8000/api/orders/create/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"buyer_id": 1, "vendor_id": 2, "payment_method": "mobile_money", ...}'

# Get notifications:
curl -X GET http://localhost:8000/api/notifications/ \
  -H "Authorization: Bearer YOUR_TOKEN"
