from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from orders.models import Order
from earnings.models import VendorEarnings

User = get_user_model()


class Command(BaseCommand):
    help = "Create earnings records for existing completed orders"

    def add_arguments(self, parser):
        parser.add_argument(
            "--vendor-id",
            type=int,
            help="Create earnings for specific vendor only",
        )

    def handle(self, *args, **options):
        vendor_filter = {}
        if options["vendor_id"]:
            vendor_filter["vendor_id"] = options["vendor_id"]

        # Get completed orders without earnings records
        completed_orders = Order.objects.filter(
            status=Order.STATUS_COMPLETED, **vendor_filter
        ).exclude(earnings__isnull=False)

        self.stdout.write(
            f"Found {completed_orders.count()} completed orders without earnings records"
        )

        created_count = 0
        for order in completed_orders:
            # Get commission rate (default 10%)
            commission_rate = 10.00
            if hasattr(order.vendor, "vendor_profile"):
                commission_rate = order.vendor.vendor_profile.commission_rate or 10.00

            VendorEarnings.objects.create(
                vendor=order.vendor,
                order=order,
                gross_amount=order.total_amount,
                commission_rate=commission_rate,
            )
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {created_count} earnings records")
        )
