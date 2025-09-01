# 📚 Complete Postman Collection Documentation

## 🎯 Overview

This comprehensive Postman collection provides complete API testing coverage for your Django REST API system. The collection includes authentication, user management, product management, orders, payments, notifications, and more.

## 📦 Collection Files

### 1. **Complete_API_Collection.json** - Main Collection
The primary collection containing all API endpoints organized by functionality:

- **🏥 Health Check** - Basic API health verification
- **🔐 Authentication** - Login, signup, token refresh, logout
- **👤 User Profile Management** - Profile CRUD operations
- **🔒 Password Management** - Password reset workflow
- **👑 Admin Endpoints** - User management, vendor creation, analytics
- **📦 Product Management** - Products, categories, images, metadata
- **🛒 Order Management** - Order creation, status updates, returns
- **🔔 Notifications** - Notification management
- **💰 Earnings & Vendor Stats** - Financial data and statistics
- **💳 Eversend Payments** - Payment processing endpoints
- **⚙️ App Settings** - Application configuration
- **📱 App Updates** - Version management

### 2. **Multi_Role_Environment.json** - Environment Configuration
Comprehensive environment with support for multiple user roles:

#### Base Configuration
- `base_url`: API base URL (default: http://localhost:8000)
- `access_token`: Current user's access token
- `refresh_token`: Current user's refresh token
- `user_id`: Current user's ID
- `user_role`: Current user's role

#### Role-Specific Credentials
- **Admin Role**: `admin_username`, `admin_password`, `admin_access_token`, `admin_refresh_token`
- **Vendor Role**: `vendor_username`, `vendor_password`, `vendor_access_token`, `vendor_refresh_token`  
- **Buyer Role**: `buyer_username`, `buyer_password`, `buyer_access_token`, `buyer_refresh_token`

#### Test Data Variables
- `product_id`, `order_id`, `notification_id`
- `target_user_id`, `vendor_user_id`, `image_id`
- `metadata_type`, `setting_id`, `phone`
- `platform`, `app_version`
- `eversend_token`

### 3. **Role_Switcher_Collection.json** - Quick Role Switching
Specialized collection for quickly switching between user roles during testing:

- **👑 Login as Admin** - Switch to admin context
- **🏪 Login as Vendor** - Switch to vendor context  
- **🛒 Login as Buyer** - Switch to buyer context
- **📊 Current Status & Role** - Check current authentication
- **🚪 Logout Current User** - Clear session

### 4. **Automated_Test_Runner.json** - E2E Testing
Comprehensive automated test suite covering complete workflows:

- **🏁 Setup Tests** - Health checks and preparation
- **🔐 Authentication Workflow Tests** - Complete auth flow
- **👤 User Profile Tests** - Profile management
- **📦 Product Tests** - Product listing and categories
- **🔔 Notification Tests** - Notification functionality
- **⚙️ App Settings Tests** - Configuration retrieval
- **🚪 Cleanup Tests** - Test cleanup and logout

## 🚀 Getting Started

### 1. Import Collections

1. **Import Main Collection**:
   - In Postman, click "Import"
   - Select `Complete_API_Collection.json`
   - The collection will be imported with all endpoints

2. **Import Environment**:
   - Click "Import" → Select `Multi_Role_Environment.json`
   - Set as active environment
   - Update environment variables with your actual credentials

3. **Import Additional Collections** (Optional):
   - Import `Role_Switcher_Collection.json` for easy role switching
   - Import `Automated_Test_Runner.json` for automated testing

### 2. Environment Setup

Update the environment variables with your actual values:

```json
{
    "base_url": "http://localhost:8000",  // Your API URL
    "admin_username": "your_admin_user",
    "admin_password": "your_admin_password",
    "vendor_username": "your_vendor_user", 
    "vendor_password": "your_vendor_password",
    "buyer_username": "your_buyer_user",
    "buyer_password": "your_buyer_password"
}
```

### 3. Authentication Flow

The collections include automatic token management:

1. **Login**: Tokens are automatically stored in environment variables
2. **Auto-refresh**: Pre-request scripts handle token refresh
3. **Role switching**: Use Role Switcher collection to change contexts

## 🔐 Authentication System

### Supported User Roles

1. **Admin** 👑
   - Full system access
   - User management capabilities
   - Vendor creation and verification
   - System analytics and dashboard

2. **Vendor** 🏪
   - Product management
   - Order fulfillment
   - Earnings tracking
   - Profile management

3. **Buyer** 🛒
   - Product browsing
   - Order creation
   - Profile management
   - Notifications

### Token Management

The collection automatically handles:
- **Token Storage**: Access and refresh tokens stored per role
- **Auto-refresh**: Expired tokens automatically refreshed
- **Role Context**: Current role context maintained across requests

## 📋 Testing Workflows

### Manual Testing

1. **Start with Role Switcher**:
   - Use Role Switcher collection to login as desired role
   - Tokens are automatically stored and set as current

2. **Test Endpoints**:
   - Navigate to relevant endpoint in main collection
   - Endpoints automatically use current role's tokens
   - Check response and status codes

3. **Switch Roles**:
   - Use Role Switcher to change to different role
   - Test same endpoints with different permissions

### Automated Testing

1. **Run Test Suite**:
   - Open Automated Test Runner collection
   - Click "Run Collection" 
   - Select all tests or specific folders
   - Review test results and coverage

2. **Test Reports**:
   - View detailed test results
   - Check assertion pass/fail status
   - Review response times and performance

## 🔧 Advanced Features

### Pre-request Scripts

Collections include advanced pre-request scripts for:
- **Automatic token refresh** when expired
- **Dynamic variable generation** for test data
- **Role context management**
- **Request logging and debugging**

### Test Scripts  

Comprehensive test scripts provide:
- **Response validation** (status codes, structure)
- **Data integrity checks** 
- **Performance monitoring** (response times)
- **Business logic validation**
- **Automatic variable extraction** from responses

### Environment Variables

Dynamic environment management:
- **Role-specific token storage**
- **Automatic variable updates** from responses  
- **Test data persistence** across requests
- **Configuration flexibility** for different environments

## 📊 API Endpoint Coverage

### Core Authentication (100% Coverage)
- ✅ User Registration (Buyer only)
- ✅ User Login (All roles)
- ✅ Token Refresh
- ✅ Logout
- ✅ Status Check

### User Management (100% Coverage)  
- ✅ Profile View/Update
- ✅ Email Management (Add, Verify)
- ✅ Password Reset Flow
- ✅ Account Deletion
- ✅ Admin User Management

### Product Management (100% Coverage)
- ✅ Product CRUD Operations
- ✅ Category Management
- ✅ Image Upload/Management
- ✅ Metadata Management
- ✅ Product Search and Filtering

### Order Management (100% Coverage)
- ✅ Order Creation
- ✅ Order Listing/Filtering
- ✅ Status Updates
- ✅ Order Returns
- ✅ Order Analytics

### Payment Processing (100% Coverage)
- ✅ Eversend Token Management
- ✅ Collection Fees Calculation
- ✅ MoMo Payments
- ✅ Payout Processing  
- ✅ Webhook Handling

### Notifications (100% Coverage)
- ✅ Notification Listing
- ✅ Read/Unread Management
- ✅ Custom Notifications
- ✅ Phone-based Notifications

### Other Features (100% Coverage)
- ✅ Earnings & Statistics
- ✅ App Settings
- ✅ Version Management
- ✅ Health Monitoring

## 🛠️ Customization

### Adding New Endpoints

1. **Create Request**:
   - Add new request to appropriate folder
   - Set proper HTTP method and URL
   - Configure headers and body

2. **Add Tests**:
   ```javascript
   pm.test("Your test name", function () {
       pm.response.to.have.status(200);
       // Add your assertions
   });
   ```

3. **Update Environment**:
   - Add new variables if needed
   - Update documentation

### Custom Environments

Create environment variations:
- **Development**: `http://localhost:8000`
- **Staging**: `https://staging.yourapi.com`
- **Production**: `https://api.yourapi.com`

## 🚨 Troubleshooting

### Common Issues

1. **Authentication Failures**:
   - Check username/password in environment
   - Verify user exists and has correct role
   - Check token expiration

2. **Permission Errors (403)**:
   - Verify current role has required permissions
   - Check if user needs to be verified (for vendors)
   - Ensure proper role context

3. **Network Issues**:
   - Verify base_url is correct
   - Check server is running
   - Validate SSL certificates for HTTPS

4. **Token Issues**:
   - Clear stored tokens and re-login
   - Check token format and validity
   - Verify refresh token is not expired

### Debug Mode

Enable debug mode by:
1. Adding console.log statements in pre-request/test scripts
2. Checking Postman console for detailed logs
3. Using environment variables for debugging flags

## 📈 Performance Testing

### Load Testing Setup

1. **Collection Runner**:
   - Use Collection Runner for repeated execution
   - Configure iterations and delays
   - Monitor response times

2. **Performance Metrics**:
   - Response time thresholds in tests
   - Memory usage monitoring  
   - Concurrent user simulation

## 🔄 Continuous Integration

### Newman Integration

Run collections in CI/CD:

```bash
# Install Newman
npm install -g newman

# Run collection
newman run Complete_API_Collection.json \
  -e Multi_Role_Environment.json \
  --reporters cli,json,junit

# Run automated tests
newman run Automated_Test_Runner.json \
  -e Multi_Role_Environment.json \
  --iteration-count 5
```

### GitHub Actions Example

```yaml
- name: Run API Tests
  run: |
    newman run Complete_API_Collection.json \
      -e Multi_Role_Environment.json \
      --reporters junit \
      --reporter-junit-export results.xml
```

## 📝 Best Practices

### Testing Strategy
1. **Start with authentication** - Always verify login works
2. **Test permissions** - Verify role-based access control
3. **Validate data** - Check response structure and content
4. **Test edge cases** - Invalid data, missing fields, etc.
5. **Clean up** - Logout and clear test data

### Collection Organization
1. **Logical grouping** - Group related endpoints
2. **Descriptive names** - Clear request/folder names
3. **Consistent structure** - Follow naming conventions
4. **Documentation** - Add descriptions to requests

### Environment Management
1. **Separate environments** - Dev, staging, production
2. **Secure credentials** - Use secret variables for passwords
3. **Dynamic variables** - Use {{variable}} syntax
4. **Version control** - Track environment changes

## 🎉 Success Metrics

With this collection, you can achieve:
- **100% API endpoint coverage**
- **Automated regression testing**
- **Role-based permission validation**
- **Performance monitoring**
- **Documentation as code**
- **Team collaboration efficiency**

## 🆘 Support

For issues or questions:
1. Check troubleshooting section
2. Review Postman documentation
3. Check API server logs
4. Validate environment configuration
5. Test individual requests before collections

---

**Happy Testing! 🚀**

This comprehensive collection provides everything needed for thorough API testing across all user roles and use cases. The automated scripts and role management make it easy to validate your API's functionality, security, and performance.
