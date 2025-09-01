from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Transaction, Wallet, Commission, Payment, Earning, AuditLog


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_ref', 'uuid', 'transaction_type', 'currency', 
        'amount', 'service_fee', 'status', 'created_at'
    ]
    list_filter = [
        'status', 'transaction_type', 'currency', 'country', 
        'created_at', 'updated_at'
    ]
    search_fields = ['transaction_ref', 'uuid', 'transaction_id', 'account_number']
    readonly_fields = ['transaction_id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('transaction_ref', 'transaction_id', 'transaction_type', 'status')
        }),
        ('User & Account', {
            'fields': ('uuid', 'account_number', 'country')
        }),
        ('Financial Details', {
            'fields': ('currency', 'amount', 'service_fee', 'charges')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of transaction records
        return False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'currency', 'amount', 'created_at', 'updated_at']
    list_filter = ['currency', 'created_at', 'updated_at']
    search_fields = ['uuid']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['uuid', 'currency']
    
    def get_queryset(self, request):
        return super().get_queryset(request)


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ['currency', 'amount', 'created_at', 'updated_at']
    list_filter = ['currency', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['currency']
    
    def changelist_view(self, request, extra_context=None):
        # Add summary statistics
        summary = Commission.objects.aggregate(
            total_commissions=Sum('amount')
        )
        extra_context = extra_context or {}
        extra_context['summary'] = summary
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_ref', 'user_uuid', 'amount', 'payment_method', 
        'status', 'created_at'
    ]
    list_filter = ['status', 'payment_method', 'created_at', 'updated_at']
    search_fields = ['transaction_ref', 'user_uuid', 'order_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Payment Info', {
            'fields': ('transaction_ref', 'order_id', 'payment_method', 'status')
        }),
        ('User & Amount', {
            'fields': ('user_uuid', 'amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Earning)
class EarningAdmin(admin.ModelAdmin):
    list_display = [
        'uuid', 'transaction_ref', 'currency', 'amount', 
        'service_name', 'status', 'created_at'
    ]
    list_filter = ['status', 'service_name', 'currency', 'created_at']
    search_fields = ['uuid', 'transaction_ref']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def changelist_view(self, request, extra_context=None):
        # Add earning statistics
        summary = Earning.objects.aggregate(
            total_earnings=Sum('amount')
        )
        extra_context = extra_context or {}
        extra_context['summary'] = summary
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'action_short', 'ip_address', 'created_at']
    list_filter = ['created_at', 'ip_address']
    search_fields = ['uuid', 'action', 'ip_address', 'user_agent']
    readonly_fields = ['uuid', 'action', 'user_agent', 'ip_address', 'created_at']
    ordering = ['-created_at']
    
    def action_short(self, obj):
        """Display truncated action for list view"""
        return obj.action[:100] + '...' if len(obj.action) > 100 else obj.action
    action_short.short_description = 'Action'
    
    def has_add_permission(self, request):
        # Prevent manual addition of audit logs
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of audit logs
        return False
    
    def has_change_permission(self, request, obj=None):
        # Make audit logs read-only
        return False


# Custom admin site configuration
admin.site.site_header = "Eversend Payments Administration"
admin.site.site_title = "Eversend Payments Admin"
admin.site.index_title = "Welcome to Eversend Payments Administration"
