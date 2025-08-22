from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, AdminProfile, VendorProfile, BuyerProfile, UserActivityLog, PasswordReset


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User admin with role-based management and financial tracking."""
    
    list_display = ('full_name', 'username', 'email','phone', 'role', 'status', 'wallet_display', 'referral_points', 
                   'verification_status', 'is_active', 'date_joined')
    list_filter = ('role', 'status', 'email_verified', 'phone_verified', 'is_active', 'is_staff')
    search_fields = ('full_name', 'username', 'email', 'phone', 'first_name', 'last_name', 'business_name')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Business Info', {
            'fields': ('role', 'business_name', 'phone', 'location')
        }),
        ('Financial Info', {
            'fields': ('wallet', 'referral_points')
        }),
        ('Security & Verification', {
            'fields': ('status', 'email_verified', 'phone_verified', 'login_attempts', 'account_locked_until')
        }),
        ('Profile', {
            'fields': ('profile_image',)
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('email', 'role', 'phone', 'business_name')
        }),
    )
    
    def wallet_display(self, obj):
        """Display wallet balance with currency formatting."""
        return f"UGX {obj.wallet:,.2f}"
    wallet_display.short_description = 'Wallet Balance'
    
    def verification_status(self, obj):
        """Display verification status with icons."""
        email_icon = "✅" if obj.email_verified else "❌"
        phone_icon = "✅" if obj.phone_verified else "❌"
        return format_html(f"Email: {email_icon} | Phone: {phone_icon}")
    verification_status.short_description = 'Verified'
    
    actions = ['verify_email', 'verify_phone', 'unlock_accounts', 'activate_users', 'deactivate_users']
    
    def verify_email(self, request, queryset):
        """Mark selected users as email verified."""
        updated = queryset.update(email_verified=True)
        self.message_user(request, f'{updated} users marked as email verified.')
    verify_email.short_description = "Mark as email verified"
    
    def verify_phone(self, request, queryset):
        """Mark selected users as phone verified."""
        updated = queryset.update(phone_verified=True)
        self.message_user(request, f'{updated} users marked as phone verified.')
    verify_phone.short_description = "Mark as phone verified"
    
    def unlock_accounts(self, request, queryset):
        """Unlock selected user accounts."""
        updated = queryset.update(account_locked_until=None, login_attempts=0)
        self.message_user(request, f'{updated} accounts unlocked.')
    unlock_accounts.short_description = "Unlock accounts"
    
    def activate_users(self, request, queryset):
        """Activate selected users."""
        updated = queryset.update(status='active', is_active=True)
        self.message_user(request, f'{updated} users activated.')
    activate_users.short_description = "Activate users"
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users."""
        updated = queryset.update(status='inactive', is_active=False)
        self.message_user(request, f'{updated} users deactivated.')
    deactivate_users.short_description = "Deactivate users"


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    """Admin interface for AdminProfile."""
    list_display = ('user', 'department', 'get_email')
    list_filter = ('department',)
    search_fields = ('user__username', 'user__email', 'department')
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    """Admin interface for VendorProfile with business verification."""
    list_display = ('user', 'business_type', 'commission_rate', 'is_verified_vendor', 'get_wallet')
    list_filter = ('business_type', 'is_verified_vendor')
    search_fields = ('user__username', 'user__business_name', 'business_type', 'business_registration_number')
    readonly_fields = ('verification_documents',)
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'business_type')
        }),
        ('Business Details', {
            'fields': ('business_registration_number', 'tax_id', 'commission_rate')
        }),
        ('Verification', {
            'fields': ('is_verified_vendor', 'verification_documents')
        }),
        ('Financial Info', {
            'fields': ('bank_account_info',),
            'classes': ('collapse',)
        }),
    )
    
    def get_wallet(self, obj):
        return f"UGX {obj.user.wallet:,.2f}"
    get_wallet.short_description = 'Wallet Balance'
    
    actions = ['verify_vendors', 'unverify_vendors']
    
    def verify_vendors(self, request, queryset):
        """Mark selected vendors as verified."""
        updated = queryset.update(is_verified_vendor=True)
        self.message_user(request, f'{updated} vendors verified.')
    verify_vendors.short_description = "Verify vendors"
    
    def unverify_vendors(self, request, queryset):
        """Mark selected vendors as unverified."""
        updated = queryset.update(is_verified_vendor=False)
        self.message_user(request, f'{updated} vendors unverified.')
    unverify_vendors.short_description = "Unverify vendors"


@admin.register(BuyerProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    """Admin interface for BuyerProfile."""
    list_display = ('user', 'loyalty_tier', 'get_wallet', 'get_phone')
    list_filter = ('loyalty_tier',)
    search_fields = ('user__username', 'user__email', 'delivery_address')
    
    def get_wallet(self, obj):
        return f"UGX {obj.user.wallet:,.2f}"
    get_wallet.short_description = 'Wallet Balance'
    
    def get_phone(self, obj):
        phones = [obj.user.phone]
        if obj.secondary_phone:
            phones.append(obj.secondary_phone)
        return " | ".join(filter(None, phones))
    get_phone.short_description = 'Phone Numbers'


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    """Admin interface for UserActivityLog with filtering and search."""
    list_display = ('user', 'action', 'description', 'ip_address', 'created_at')
    list_filter = ('action', 'created_at', 'user__role')
    search_fields = ('user__username', 'user__email', 'description', 'ip_address')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Activity Info', {
            'fields': ('user', 'action', 'description')
        }),
        ('Technical Info', {
            'fields': ('ip_address', 'user_agent', 'metadata')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual creation of activity logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make activity logs read-only."""
        return False
    

@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ("user", "email", "verification_code", "expires_at", "created_at" )
    