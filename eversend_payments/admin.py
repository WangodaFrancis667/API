from django.contrib import admin
from .models import Transaction, Wallet, Commission, Payment, AuditLog

admin.site.register(Transaction)
admin.site.register(Wallet)
admin.site.register(Commission)
admin.site.register(Payment)
admin.site.register(AuditLog)
