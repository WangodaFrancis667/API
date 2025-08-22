# Postman API Testing Setup Guide

## Complete Guide for Testing API Endpoints with Automatic Bearer Token Management

This comprehensive guide will walk you through setting up Postman for testing all API endpoints in this Django project with automatic Bearer token management across different user roles (Admin, Vendor, Buyer).

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Authentication Setup](#authentication-setup)
4. [Collection Structure](#collection-structure)
5. [API Endpoints by Module](#api-endpoints-by-module)
6. [Testing Workflows](#testing-workflows)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## Prerequisites

- **Postman Application**: Download and install from [postman.com](https://www.postman.com/)
- **Django Server Running**: Ensure your Django development server is running on `localhost:8000`
- **Test User Accounts**: Have test accounts for each role (Admin, Vendor, Buyer)
- **Basic Postman Knowledge**: Understanding of requests, collections, and environments

---

## Environment Setup

### Step 1: Create New Environment

1. **Open Postman** and click on **"Environments"** in the left sidebar
2. **Click "Create Environment"** or the **"+"** button
3. **Name**: `Product Management API - Development`
4. **Add the following variables**:

| Variable Name | Initial Value | Current Value | Description |
|---------------|---------------|---------------|-------------|
| `base_url` | `http://localhost:8000/api` | `http://localhost:8000/api` | Base API URL |
| `access_token` | *(leave empty)* | *(leave empty)* | Current active token |
| `admin_token` | *(leave empty)* | *(leave empty)* | Admin user token |
| `vendor_token` | *(leave empty)* | *(leave empty)* | Vendor user token |
| `buyer_token` | *(leave empty)* | *(leave empty)* | Buyer user token |
| `refresh_token` | *(leave empty)* | *(leave empty)* | Current refresh token |
| `user_id` | *(leave empty)* | *(leave empty)* | Current user ID |
| `product_id` | *(leave empty)* | *(leave empty)* | For testing specific products |
| `order_id` | *(leave empty)* | *(leave empty)* | For testing specific orders |
| `notification_id` | *(leave empty)* | *(leave empty)* | For testing specific notifications |

5. **Save** the environment and **select it** from the environment dropdown

---

## Authentication Setup

### Step 2: Create Authentication Collection

1. **Create new collection**: Name it `"Authentication"`
2. **Set Collection Authorization**: 
   - Type: `No Auth` (we'll handle it per request)

### Step 3: Login Requests with Automatic Token Storage

#### A. Admin Login Request

**Create New Request:**
- **Name**: `Admin Login`
- **Method**: `POST`
- **URL**: `{{base_url}}/auth/login/`

**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
  "email": "admin@example.com",
  "password": "your_admin_password"
}
```

**Tests Script (Critical - This saves the token automatically):**
```javascript
// Parse the response
const responseJson = pm.response.json();

// Check if login was successful
if (pm.response.code === 200 && responseJson.access_token) {
    // Store tokens in environment variables
    pm.environment.set("admin_token", responseJson.access_token);
    pm.environment.set("access_token", responseJson.access_token);
    pm.environment.set("refresh_token", responseJson.refresh_token);
    
    // Store user info if available
    if (responseJson.user) {
        pm.environment.set("user_id", responseJson.user.id);
    }
    
    // Console log for confirmation
    console.log("✅ Admin login successful!");
    console.log("🔑 Access token stored:", responseJson.access_token.substring(0, 20) + "...");
    
    // Set test result
    pm.test("Admin login successful", function () {
        pm.response.to.have.status(200);
        pm.expect(responseJson.access_token).to.be.a('string');
    });
} else {
    console.log("❌ Admin login failed");
    pm.test("Admin login failed", function () {
        pm.response.to.have.status(200);
    });
}
```

#### B. Vendor Login Request

**Create New Request:**
- **Name**: `Vendor Login`
- **Method**: `POST`
- **URL**: `{{base_url}}/auth/login/`

**Body (raw JSON):**
```json
{
  "email": "vendor@example.com",
  "password": "your_vendor_password"
}
```

**Tests Script:**
```javascript
const responseJson = pm.response.json();

if (pm.response.code === 200 && responseJson.access_token) {
    pm.environment.set("vendor_token", responseJson.access_token);
    pm.environment.set("access_token", responseJson.access_token);
    pm.environment.set("refresh_token", responseJson.refresh_token);
    
    if (responseJson.user) {
        pm.environment.set("user_id", responseJson.user.id);
    }
    
    console.log("✅ Vendor login successful!");
    console.log("🔑 Access token stored:", responseJson.access_token.substring(0, 20) + "...");
    
    pm.test("Vendor login successful", function () {
        pm.response.to.have.status(200);
        pm.expect(responseJson.access_token).to.be.a('string');
    });
} else {
    console.log("❌ Vendor login failed");
}
```

#### C. Buyer Login Request

**Create New Request:**
- **Name**: `Buyer Login`
- **Method**: `POST`
- **URL**: `{{base_url}}/auth/login/`

**Body (raw JSON):**
```json
{
  "email": "buyer@example.com",
  "password": "your_buyer_password"
}
```

**Tests Script:**
```javascript
const responseJson = pm.response.json();

if (pm.response.code === 200 && responseJson.access_token) {
    pm.environment.set("buyer_token", responseJson.access_token);
    pm.environment.set("access_token", responseJson.access_token);
    pm.environment.set("refresh_token", responseJson.refresh_token);
    
    if (responseJson.user) {
        pm.environment.set("user_id", responseJson.user.id);
    }
    
    console.log("✅ Buyer login successful!");
    console.log("🔑 Access token stored:", responseJson.access_token.substring(0, 20) + "...");
    
    pm.test("Buyer login successful", function () {
        pm.response.to.have.status(200);
        pm.expect(responseJson.access_token).to.be.a('string');
    });
} else {
    console.log("❌ Buyer login failed");
}
```

### Step 4: Token Management Utilities

#### Switch to Admin Token
**Create New Request:**
- **Name**: `🔄 Switch to Admin Token`
- **Method**: `GET`
- **URL**: `{{base_url}}/auth/status/` (dummy endpoint to test token)

**Pre-request Script:**
```javascript
// Switch to admin token
const adminToken = pm.environment.get("admin_token");
if (adminToken) {
    pm.environment.set("access_token", adminToken);
    console.log("🔄 Switched to Admin token");
} else {
    console.log("❌ No Admin token found. Please login as Admin first.");
}
```

**Tests Script:**
```javascript
pm.test("Token switch successful", function () {
    const currentToken = pm.environment.get("access_token");
    const adminToken = pm.environment.get("admin_token");
    pm.expect(currentToken).to.eql(adminToken);
});
```

#### Switch to Vendor Token
**Create New Request:**
- **Name**: `🔄 Switch to Vendor Token`
- **Method**: `GET`
- **URL**: `{{base_url}}/auth/status/`

**Pre-request Script:**
```javascript
const vendorToken = pm.environment.get("vendor_token");
if (vendorToken) {
    pm.environment.set("access_token", vendorToken);
    console.log("🔄 Switched to Vendor token");
} else {
    console.log("❌ No Vendor token found. Please login as Vendor first.");
}
```

#### Switch to Buyer Token
**Create New Request:**
- **Name**: `🔄 Switch to Buyer Token`
- **Method**: `GET`
- **URL**: `{{base_url}}/auth/status/`

**Pre-request Script:**
```javascript
const buyerToken = pm.environment.get("buyer_token");
if (buyerToken) {
    pm.environment.set("access_token", buyerToken);
    console.log("🔄 Switched to Buyer token");
} else {
    console.log("❌ No Buyer token found. Please login as Buyer first.");
}
```

---

## Collection Structure

Create the following folder structure in Postman:

```
📁 Product Management API
├── 📁 Authentication
│   ├── Admin Login
│   ├── Vendor Login
│   ├── Buyer Login
│   ├── 🔄 Switch to Admin Token
│   ├── 🔄 Switch to Vendor Token
│   ├── 🔄 Switch to Buyer Token
│   ├── Token Refresh
│   ├── Logout
│   └── Check Auth Status
├── 📁 Account Management
│   ├── User Profile
│   ├── Update Profile
│   ├── Password Reset
│   └── Email Verification
├── 📁 Product Management
│   ├── 📁 Categories
│   ├── 📁 Product Metadata
│   ├── 📁 Product CRUD
│   ├── 📁 Product Viewing
│   └── 📁 Product Images
├── 📁 Order Management
│   ├── Create Order
│   ├── Order List
│   ├── Update Order Status
│   └── Create Return
├── 📁 Notifications
│   ├── List Notifications
│   ├── Mark as Read
│   ├── Delete Notifications
│   └── Custom Notifications
├── 📁 App Settings
│   ├── Get Settings
│   └── Update Settings
└── 📁 Admin Operations
    ├── User Management
    ├── Vendor Verification
    └── System Statistics
```

---

## API Endpoints by Module

### Authentication Endpoints (`/api/auth/`)

#### 1. User Signup
- **Method**: `POST`
- **URL**: `{{base_url}}/auth/signup/`
- **Headers**: `Content-Type: application/json`
- **Body**:
```json
{
  "email": "newuser@example.com",
  "password": "securePassword123",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "user_type": "buyer"
}
```

#### 2. Token Refresh
- **Method**: `POST`
- **URL**: `{{base_url}}/auth/token/refresh/`
- **Headers**: 
  - `Content-Type: application/json`
  - `Authorization: Bearer {{access_token}}`
- **Body**:
```json
{
  "refresh": "{{refresh_token}}"
}
```

**Tests Script:**
```javascript
const responseJson = pm.response.json();
if (pm.response.code === 200 && responseJson.access_token) {
    pm.environment.set("access_token", responseJson.access_token);
    console.log("🔄 Token refreshed successfully");
}
```

#### 3. User Profile
- **Method**: `GET`
- **URL**: `{{base_url}}/auth/profile/`
- **Headers**: `Authorization: Bearer {{access_token}}`

#### 4. Update Profile
- **Method**: `PUT`
- **URL**: `{{base_url}}/auth/update-profile/`
- **Headers**: 
  - `Content-Type: application/json`
  - `Authorization: Bearer {{access_token}}`
- **Body**:
```json
{
  "first_name": "John Updated",
  "last_name": "Doe Updated",
  "phone_number": "+1234567891"
}
```

### Product Management Endpoints (`/api/products/`)

#### Categories

#### 5. Get All Categories
- **Method**: `GET`
- **URL**: `{{base_url}}/products/categories/`
- **Headers**: `Authorization: Bearer {{access_token}}`

#### Product Metadata

#### 6. Get All Product Metadata
- **Method**: `GET`
- **URL**: `{{base_url}}/products/metadata/`
- **Headers**: `Authorization: Bearer {{access_token}}`

#### 7. Create Product Metadata (Admin Only)
- **Method**: `POST`
- **URL**: `{{base_url}}/products/metadata/`
- **Headers**: 
  - `Content-Type: application/json`
  - `Authorization: Bearer {{admin_token}}`
- **Body**:
```json
{
  "type": "category",
  "name": "electronics",
  "display_name": "Electronics",
  "description": "Electronic devices and accessories",
  "category_type": "physical",
  "is_active": true,
  "sort_order": 1
}
```

#### 8. Get Metadata by Type
- **Method**: `GET`
- **URL**: `{{base_url}}/products/metadata/type/category/`
- **Headers**: `Authorization: Bearer {{access_token}}`

#### Product CRUD

#### 9. Create Product (Vendor/Admin Only)
- **Method**: `POST`
- **URL**: `{{base_url}}/products/create/`
- **Headers**: 
  - `Content-Type: application/json`
  - `Authorization: Bearer {{vendor_token}}`
- **Body**:
```json
{
  "title": "iPhone 15 Pro",
  "description": "Latest iPhone with advanced features",
  "regular_price": "999.00",
  "group_price": "950.00",
  "min_quantity": 1,
  "unit": "piece",
  "category": 1,
  "is_active": true
}
```

**Tests Script:**
```javascript
const responseJson = pm.response.json();
if (pm.response.code === 201 && responseJson.id) {
    pm.environment.set("product_id", responseJson.id);
    console.log("📦 Product created with ID:", responseJson.id);
}
```

#### 10. Update Product
- **Method**: `PUT`
- **URL**: `{{base_url}}/products/{{product_id}}/update/`
- **Headers**: 
  - `Content-Type: application/json`
  - `Authorization: Bearer {{vendor_token}}`

#### 11. Delete Product (Soft Delete)
- **Method**: `DELETE`
- **URL**: `{{base_url}}/products/{{product_id}}/delete/`
- **Headers**: `Authorization: Bearer {{vendor_token}}`

#### 12. Hard Delete Product (Admin Only)
- **Method**: `DELETE`
- **URL**: `{{base_url}}/products/{{product_id}}/hard-delete/`
- **Headers**: `Authorization: Bearer {{admin_token}}`

#### Product Viewing

#### 13. Get All Products
- **Method**: `GET`
- **URL**: `{{base_url}}/products/view-products/`
- **Headers**: `Authorization: Bearer {{access_token}}`

#### 14. Get Products with Filters
- **Method**: `GET`
- **URL**: `{{base_url}}/products/view-products/?category=1&min_price=100&max_price=1000&ordering=-created_at`
- **Headers**: `Authorization: Bearer {{access_token}}`

#### 15. Get Product Details
- **Method**: `GET`
- **URL**: `{{base_url}}/products/product-details/{{product_id}}/`
- **Headers**: `Authorization: Bearer {{access_token}}`

#### Product Images

#### 16. Get Product Images
- **Method**: `GET`
- **URL**: `{{base_url}}/products/{{product_id}}/images/`
- **Headers**: `Authorization: Bearer {{access_token}}`

#### 17. Upload Product Image
- **Method**: `POST`
- **URL**: `{{base_url}}/products/{{product_id}}/images/`
- **Headers**: 
  - `Authorization: Bearer {{vendor_token}}`
- **Body**: `form-data`
  - Key: `image` (File)
  - Value: Select image file

### Order Management Endpoints (`/api/orders/`)

#### 18. Create Order
- **Method**: `POST`
- **URL**: `{{base_url}}/orders/create/`
- **Headers**: 
  - `Content-Type: application/json`
  - `Authorization: Bearer {{buyer_token}}`
- **Body**:
```json
{
  "items": [
    {
      "product_id": 1,
      "quantity": 2,
      "unit_price": "999.00"
    }
  ],
  "delivery_address": "123 Main St, City, State 12345",
  "payment_method": "card"
}
```

#### 19. Get Order List
- **Method**: `GET`
- **URL**: `{{base_url}}/orders/list/`
- **Headers**: `Authorization: Bearer {{access_token}}`

#### 20. Update Order Status (Admin/Vendor Only)
- **Method**: `PATCH`
- **URL**: `{{base_url}}/orders/status/`
- **Headers**: 
  - `Content-Type: application/json`
  - `Authorization: Bearer {{admin_token}}`
- **Body**:
```json
{
  "order_id": 1,
  "status": "shipped"
}
```

### Notification Endpoints (`/api/notifications/`)

#### 21. Get Notifications
- **Method**: `GET`
- **URL**: `{{base_url}}/notifications/`
- **Headers**: `Authorization: Bearer {{access_token}}`

#### 22. Get Unread Count
- **Method**: `GET`
- **URL**: `{{base_url}}/notifications/unread-count/`
- **Headers**: `Authorization: Bearer {{access_token}}`

#### 23. Mark as Read
- **Method**: `POST`
- **URL**: `{{base_url}}/notifications/mark-read/`
- **Headers**: 
  - `Content-Type: application/json`
  - `Authorization: Bearer {{access_token}}`
- **Body**:
```json
{
  "notification_id": 1
}
```

### App Settings Endpoints (`/api/app/`)

#### 24. Get App Settings
- **Method**: `GET`
- **URL**: `{{base_url}}/app/app-settings/`
- **Headers**: `Authorization: Bearer {{access_token}}`

---

## Testing Workflows

### Workflow 1: Complete User Journey Test

**Order of Execution:**
1. **Admin Login** → Test admin-specific endpoints
2. **Create Product Metadata** (as Admin)
3. **Switch to Vendor Token**
4. **Create Product** (as Vendor)
5. **Upload Product Images** (as Vendor)
6. **Switch to Buyer Token**
7. **View Products** (as Buyer)
8. **Create Order** (as Buyer)
9. **Switch to Admin Token**
10. **Update Order Status** (as Admin)

### Workflow 2: Role-Based Permission Testing

**Test Permissions:**
- Try accessing admin endpoints with vendor token (should fail)
- Try creating products with buyer token (should fail)
- Try viewing orders with different user tokens

### Workflow 3: Data Flow Testing

**Test Data Consistency:**
- Create product → View in product list → Order product → Check order details

---

## Collection-Level Scripts

### Collection Pre-request Script
Add this to your collection's Pre-request Scripts tab:

```javascript
// Auto-check token expiry and refresh if needed
const accessToken = pm.environment.get("access_token");
const refreshToken = pm.environment.get("refresh_token");

if (accessToken) {
    // Decode JWT to check expiry (basic check)
    try {
        const tokenParts = accessToken.split('.');
        if (tokenParts.length === 3) {
            const payload = JSON.parse(atob(tokenParts[1]));
            const now = Math.floor(Date.now() / 1000);
            
            if (payload.exp && payload.exp < now) {
                console.log("⚠️ Token expired, consider refreshing");
            }
        }
    } catch (e) {
        console.log("Could not decode token");
    }
}

// Log current user context
console.log("🔑 Current token:", accessToken ? accessToken.substring(0, 20) + "..." : "None");
```

### Collection Tests Script
Add this to your collection's Tests tab:

```javascript
// Global tests that run after each request
pm.test("Response time is less than 5000ms", function () {
    pm.expect(pm.response.responseTime).to.be.below(5000);
});

pm.test("Response has proper content type", function () {
    const contentType = pm.response.headers.get("content-type");
    if (contentType) {
        pm.expect(contentType).to.include("application/json");
    }
});

// Log response for debugging
if (pm.response.code >= 400) {
    console.log("❌ Error Response:", pm.response.json());
}
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. "Token not found" Error
**Problem**: Getting authentication errors
**Solution**: 
- Run the appropriate login request first
- Check if token is stored: `console.log(pm.environment.get("access_token"))`
- Ensure environment is selected

#### 2. "Permission denied" Error
**Problem**: Getting 403 Forbidden responses
**Solution**:
- Switch to appropriate user role token
- Check user permissions in Django admin
- Verify endpoint requires correct user type

#### 3. Token Expiry Issues
**Problem**: Token expires during testing
**Solution**:
- Use the Token Refresh request
- Implement automatic refresh in collection pre-request script
- Set shorter test sessions

#### 4. Environment Variables Not Updating
**Problem**: Tokens not saving automatically
**Solution**:
- Check Tests script in login requests
- Ensure environment is selected (not using globals)
- Refresh Postman if needed

### Debugging Tips

#### Enable Console Logging
Add to any request's Tests script:
```javascript
console.log("Response:", pm.response.json());
console.log("Status:", pm.response.code);
console.log("Headers:", pm.response.headers.toJSON());
```

#### Check Environment Variables
Add to Pre-request Script:
```javascript
console.log("All environment variables:");
const env = pm.environment.toObject();
Object.keys(env).forEach(key => {
    console.log(`${key}:`, env[key]);
});
```

---

## Best Practices

### 1. Request Organization
- Use folders to group related endpoints
- Use consistent naming conventions
- Add descriptions to requests
- Use meaningful test names

### 2. Token Management
- Always store tokens in environment variables
- Use descriptive variable names
- Implement token refresh logic
- Clear sensitive data when done testing

### 3. Test Data Management
- Use environment variables for IDs
- Create data cleanup requests
- Use realistic test data
- Document required test accounts

### 4. Error Handling
- Add appropriate tests for error cases
- Test with invalid tokens
- Test with malformed requests
- Verify error response formats

### 5. Documentation
- Add request descriptions
- Document required permissions
- Include example responses
- Keep README updated

### 6. Security Considerations
- Never commit real credentials
- Use test accounts only
- Clear tokens after testing sessions
- Use HTTPS in production environments

---

## Quick Start Checklist

- [ ] ✅ Postman installed and updated
- [ ] ✅ Environment created with all variables
- [ ] ✅ Test user accounts ready (Admin, Vendor, Buyer)
- [ ] ✅ Django server running on localhost:8000
- [ ] ✅ Authentication collection created
- [ ] ✅ Login requests created with Tests scripts
- [ ] ✅ Token switching utilities created
- [ ] ✅ Main API collections organized
- [ ] ✅ First successful login and token storage
- [ ] ✅ Test API endpoints working
- [ ] ✅ Role-based testing verified

---

## Support and Maintenance

### Regular Updates
- Keep Postman updated
- Update environment URLs for different stages
- Refresh test data periodically
- Update documentation as API evolves

### Team Collaboration
- Export and share collections
- Use team workspaces
- Document any custom workflows
- Share environment templates (without sensitive data)

---

**Happy Testing! 🚀**

For additional support or questions about specific endpoints, refer to the individual API documentation or contact the development team.
