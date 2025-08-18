# API Authentication System Documentation

## Overview

This Django REST API implements a comprehensive JWT-based authentication system with role-based access control. The system supports three user roles: **Admin**, **Vendor**, and **Buyer**, each with specific permissions and capabilities.

## Authentication Architecture

### JWT Token System
- **Access Token**: Short-lived token (60 minutes) for API authentication
- **Refresh Token**: Long-lived token (7 days) for obtaining new access tokens
- **Token Storage**: Tokens can be stored in HTTP-only cookies or Authorization headers
- **Token Rotation**: Refresh tokens are rotated on use for enhanced security

### Custom Authentication Class
The API uses `CookieJWTAuthentication` which extends `JWTAuthentication` to support:
- Standard `Authorization: Bearer <token>` header
- HTTP-only cookie-based authentication (`access_token` cookie)

### User Roles & Permissions

#### Admin
- **Capabilities**: Full system access, user management, vendor creation/verification
- **Endpoints**: All endpoints + admin-specific operations
- **Registration**: Manual creation only

#### Vendor  
- **Capabilities**: Business operations, profile management
- **Endpoints**: Standard user endpoints + vendor-specific features
- **Registration**: Admin-created only, requires verification
- **Status**: Pending → Active (after admin verification)

#### Buyer
- **Capabilities**: Standard user operations, purchases
- **Endpoints**: Public registration, profile management, shopping
- **Registration**: Self-registration via `/api/auth/signup/`

## API Endpoints

### Base URL: `http://localhost:8000`

### 🏥 Health Check
```
GET /health/
```
System health status with database, Redis, and server information.

### 🔐 Authentication Endpoints

#### User Registration (Buyers Only)
```
POST /api/auth/signup/
Content-Type: application/json

{
    "full_name": "John Doe",
    "phone": "+256701234567",
    "location": "Kampala, Uganda", 
    "password": "SecurePassword123!",
    "confirm_password": "SecurePassword123!"
}
```

#### User Login
```
POST /api/auth/login/
Content-Type: application/json

{
    "username": "+256701234567",  // Can be phone or username
    "password": "SecurePassword123!"
}
```

**Response:**
```json
{
    "user": {
        "id": 1,
        "full_name": "John Doe",
        "email": "john@example.com",
        "role": "buyer",
        "phone": "+256701234567",
        "location": "Kampala, Uganda",
        "profile_image": null
    },
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "message": "Logged in successfully"
}
```

#### Token Refresh
```
POST /api/auth/token/refresh/
Content-Type: application/json

{
    "refresh": "your_refresh_token_here"
}
```

#### Check Authentication Status
```
GET /api/auth/status/
Authorization: Bearer <access_token>
```

#### User Logout
```
POST /api/auth/logout/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "refresh_token": "your_refresh_token_here"
}
```

### 👤 Profile Management

#### Get User Profile
```
GET /api/auth/profile/
Authorization: Bearer <access_token>
```

#### Update Profile
```
PATCH /api/auth/update-profile/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "full_name": "Updated Name",
    "location": "New Location"
}
```

### 🔑 Password Management

#### Request Password Reset
```
POST /api/auth/password-reset/request/
Content-Type: application/json

{
    "email_or_phone": "+256701234567",
    "is_email": false
}
```

#### Verify Reset Token
```
POST /api/auth/password-reset/verify/
Content-Type: application/json

{
    "uidb64": "encoded_user_id",
    "token": "reset_token"
}
```

#### Confirm Password Reset
```
POST /api/auth/password-reset/confirm/
Content-Type: application/json

{
    "uidb64": "encoded_user_id",
    "token": "reset_token", 
    "new_password": "NewSecurePassword123!"
}
```

### ✉️ Email Verification

#### Add Email Address
```
POST /api/auth/add-email/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "email": "user@example.com"
}
```

#### Send Verification Code
```
POST /api/auth/email/send/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "email": "user@example.com"
}
```

#### Confirm Email Verification
```
POST /api/auth/email/confirm/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "email": "user@example.com",
    "verification_code": "123456"
}
```

### 👑 Admin Operations

#### Create Vendor Account
```
POST /api/auth/admin/vendor/create/
Authorization: Bearer <admin_access_token>
Content-Type: application/json

{
    "full_name": "Jane Vendor",
    "phone": "+256701234568",
    "location": "Kampala, Uganda",
    "business_type": "Electronics",
    "business_registration_number": "REG123456",
    "password": "VendorPassword123!",
    "password_confirm": "VendorPassword123!"
}
```

#### List All Users
```
GET /api/auth/admin/users/
Authorization: Bearer <admin_access_token>
```

#### Get User Details
```
GET /api/auth/admin/users/{user_id}/
Authorization: Bearer <admin_access_token>
```

#### Verify Vendor
```
POST /api/auth/admin/vendor/{user_id}/verify/
Authorization: Bearer <admin_access_token>
Content-Type: application/json

{
    "is_verified": true,
    "verification_notes": "Documents verified successfully"
}
```

### 📊 Activity & Analytics

#### Get Activity Logs
```
GET /api/auth/activity-logs/
Authorization: Bearer <access_token>
```

#### Get Dashboard Stats
```
GET /api/auth/dashboard/stats/
Authorization: Bearer <access_token>
```

### 🗑️ Account Management

#### Delete Account
```
POST /api/auth/delete-account/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "password": "current_password",
    "confirm_deletion": true
}
```

## Security Features

### Rate Limiting
- **Registration**: 10 attempts per 5 minutes per IP
- **Login**: 5 attempts per minute
- **Password Reset**: 3 attempts per hour per IP
- **Email Verification**: 1 email per minute per user

### Account Security
- **Failed Login Protection**: Account locked after multiple failed attempts
- **Password Validation**: Strong password requirements
- **Suspicious Activity Detection**: Automatic logging and monitoring
- **Session Management**: Secure cookie settings with HttpOnly and SameSite

### Data Security
- **Password Hashing**: Django's PBKDF2 algorithm
- **Input Validation**: Comprehensive serializer validation
- **SQL Injection Protection**: Django ORM
- **XSS Protection**: Built-in Django protections
- **CSRF Protection**: CSRF tokens for state-changing operations

## Using the Postman Collection

### 1. Import Collection
1. Download `API_Testing_Postman_Collection.json`
2. Open Postman
3. Click "Import" > "Choose Files" > Select the JSON file
4. The collection will be imported with all endpoints and tests

### 2. Environment Setup
The collection uses variables for flexibility:
- `{{base_url}}`: API base URL (default: http://localhost:8000)
- `{{access_token}}`: Automatically set after login
- `{{refresh_token}}`: Automatically set after login
- `{{user_id}}`: Automatically set after login

### 3. Testing Workflow

#### Basic User Flow:
1. **Health Check** - Verify API is running
2. **User Registration** - Create buyer account
3. **User Login** - Authenticate and get tokens
4. **Profile Management** - Update user information
5. **Email Verification** - Add and verify email
6. **Activity Logs** - View user activities

#### Admin Flow:
1. **Admin Login** - Use admin credentials
2. **Create Vendor** - Create vendor accounts
3. **List Users** - View all system users
4. **Verify Vendor** - Approve vendor accounts
5. **Dashboard Stats** - View system statistics

### 4. Automated Testing
The collection includes JavaScript tests that:
- Extract and store tokens automatically
- Validate response structures
- Check status codes
- Set environment variables

### 5. Error Handling
The API provides detailed error responses:
```json
{
    "error": "Invalid credentials",
    "details": "Account is temporarily locked due to multiple failed login attempts."
}
```

## Development Setup

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py makemigrations
python manage.py migrate

# Create superuser (Admin)
python manage.py createsuperuser

# Start Redis (required for caching)
redis-server

# Start Celery worker (for background tasks)
celery -A main worker -l info

# Run development server
python manage.py runserver
```

### Environment Variables (.env)
```env
SECRET_KEY=your_secret_key_here
DEBUG=True
DB_NAME=your_db_name
DB_USER=your_db_user  
DB_PASS=your_db_password
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
REDIS_URL=redis://127.0.0.1:6379/1
FRONTEND_URL=http://localhost:3000
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

## API Response Formats

### Success Response
```json
{
    "message": "Operation successful",
    "data": { /* response data */ },
    "status": "success"
}
```

### Error Response
```json
{
    "error": "Error message",
    "details": "Detailed error description",
    "field_errors": { 
        "field_name": ["Field-specific error messages"]
    }
}
```

### Validation Error
```json
{
    "email": ["This field is required."],
    "password": ["Password must be at least 8 characters long."]
}
```

## Common HTTP Status Codes
- `200 OK`: Successful request
- `201 Created`: Resource created successfully  
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Troubleshooting

### Common Issues

1. **Token Expired**
   - Use refresh token to get new access token
   - Re-login if refresh token expired

2. **Permission Denied**
   - Ensure user has correct role for endpoint
   - Check if account is active/verified

3. **Rate Limited**
   - Wait for rate limit window to reset
   - Contact admin if persistent issues

4. **Email Not Verified**
   - Send verification code
   - Check email and confirm with code

5. **Account Locked**
   - Wait for auto-unlock or contact admin
   - Account unlocks automatically after timeout

### Debug Mode
Enable Django DEBUG mode for detailed error messages during development.

## Support
For technical support or questions about the API, please refer to the system logs or contact the development team.
