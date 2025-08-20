# API Testing Setup Guide

## 🚀 Quick Start

### 1. Import Postman Collection
1. Open Postman
2. Click **Import** button
3. Select `API_Testing_Postman_Collection.json`
4. Import `Postman_Environment.json` as environment

### 2. Setup Environment 
- Set `base_url` to your API server (default: `http://localhost:8000`)
- Tokens will be automatically populated after login

### 3. Start Testing
1. **Health Check** - Verify API is running
2. **User Registration** - Create a buyer account
3. **Login** - Authenticate and get tokens (auto-stored)
4. **Explore** - Test other endpoints with authentication

## 📁 Files Included

- `API_Testing_Postman_Collection.json` - Complete Postman collection
- `Postman_Environment.json` - Environment variables
- `API_Documentation.md` - Detailed API documentation

## 🔐 Authentication System Summary

**JWT-based authentication with 3 user roles:**
- **Buyer** - Self-registration, basic user operations
- **Vendor** - Admin-created, business operations, requires verification
- **Admin** - Full system access, user management

**Key Features:**
- JWT tokens (60min access, 7-day refresh)
- Cookie + Bearer token support
- Rate limiting & security protections
- Email verification system
- Password reset functionality
- Activity logging
- Role-based permissions

## 🛠 Development Server Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Start Redis (required)
redis-server

# Start server
python manage.py runserver
```

## 📱 Test User Creation

### Create Buyer (Public Registration)
```json
POST /api/auth/signup/
{
    "full_name": "John Doe",
    "phone": "+256701234567", 
    "location": "Kampala, Uganda",
    "password": "SecurePassword123!",
    "confirm_password": "SecurePassword123!"
}
```

### Login
```json
POST /api/auth/login/
{
    "username": "+256701234567",
    "password": "SecurePassword123!"
}
```

## 🔧 Common Issues

1. **Server not running** - Check `http://localhost:8000/health/`
2. **Database issues** - Run migrations: `python manage.py migrate`
3. **Redis not running** - Start Redis: `redis-server` 
4. **Token expired** - Use refresh endpoint or login again

## 📖 Documentation

See `API_Documentation.md` for complete API reference including:
- All endpoints with examples
- Security features
- Error handling
- Development setup
- Troubleshooting guide
