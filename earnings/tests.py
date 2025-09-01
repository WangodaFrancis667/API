from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal

from orders.models import Order
from .models import VendorEarnings, VendorPayout
from .utils import get_date_range

User = get_user_model()


class EarningsModelsTestCase(TestCase):
    """Test earnings models"""
    
    def setUp(self):
        self.vendor = User.objects.create_user(
            username='testvendor',
            email='vendor@test.com',
            password='testpass123',
            role='vendor',
            business_name='Test Business'
        )
        
        self.buyer = User.objects.create_user(
            username='testbuyer',
            email='buyer@test.com',
            password='testpass123',
            role='buyer'
        )
    
    def test_vendor_earnings_creation(self):
        """Test VendorEarnings model creation and calculations"""
        # Create an order with pending status first
        order = Order.objects.create(
            user=self.buyer,
            vendor=self.vendor,
            total_amount=Decimal('100.00'),
            payment_method='card',
            delivery_address='Test Address',
            status=Order.STATUS_PENDING  # Start with pending
        )
        
        # Create earnings manually
        earnings = VendorEarnings.objects.create(
            vendor=self.vendor,
            order=order,
            gross_amount=Decimal('100.00'),
            commission_rate=Decimal('10.00')
        )
        
        # Check calculations
        self.assertEqual(earnings.commission_amount, Decimal('10.00'))
        self.assertEqual(earnings.net_earnings, Decimal('90.00'))
        self.assertEqual(str(earnings), f"Earnings for {self.vendor.username} - Order #{order.id}")
    
    def test_vendor_earnings_signal(self):
        """Test that VendorEarnings is automatically created when order is completed"""
        # Create an order with pending status
        order = Order.objects.create(
            user=self.buyer,
            vendor=self.vendor,
            total_amount=Decimal('100.00'),
            payment_method='card',
            delivery_address='Test Address',
            status=Order.STATUS_PENDING
        )
        
        # Should be no earnings record yet
        self.assertFalse(hasattr(order, 'earnings'))
        
        # Complete the order
        order.status = Order.STATUS_COMPLETED
        order.save()
        
        # Now earnings should be created automatically
        order.refresh_from_db()
        self.assertTrue(hasattr(order, 'earnings'))
        earnings = order.earnings
        self.assertEqual(earnings.vendor, self.vendor)
        self.assertEqual(earnings.gross_amount, Decimal('100.00'))
    
    def test_vendor_payout_creation(self):
        """Test VendorPayout model creation"""
        payout = VendorPayout.objects.create(
            vendor=self.vendor,
            amount=Decimal('90.00'),
            payout_method=VendorPayout.PAYOUT_BANK,
            reference_number='REF123'
        )
        
        self.assertEqual(payout.vendor, self.vendor)
        self.assertEqual(payout.amount, Decimal('90.00'))
        self.assertEqual(payout.status, VendorPayout.STATUS_PENDING)


class EarningsAPITestCase(APITestCase):
    """Test earnings API endpoints"""
    
    def setUp(self):
        self.vendor = User.objects.create_user(
            username='testvendor',
            email='vendor@test.com',
            password='testpass123',
            role='vendor',
            business_name='Test Business',
            wallet=Decimal('50.00')
        )
        
        self.buyer = User.objects.create_user(
            username='testbuyer',
            email='buyer@test.com',
            password='testpass123',
            role='buyer'
        )
        
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='adminpass123',
            role='admin'
        )
        
        # Create some test orders
        self.order1 = Order.objects.create(
            user=self.buyer,
            vendor=self.vendor,
            total_amount=Decimal('100.00'),
            payment_method='card',
            delivery_address='Test Address 1',
            status=Order.STATUS_COMPLETED
        )
        
        self.order2 = Order.objects.create(
            user=self.buyer,
            vendor=self.vendor,
            total_amount=Decimal('200.00'),
            payment_method='cash',
            delivery_address='Test Address 2',
            status=Order.STATUS_COMPLETED
        )
        
        # Create earnings
        VendorEarnings.objects.create(
            vendor=self.vendor,
            order=self.order1,
            gross_amount=Decimal('100.00'),
            commission_rate=Decimal('10.00')
        )
        
        VendorEarnings.objects.create(
            vendor=self.vendor,
            order=self.order2,
            gross_amount=Decimal('200.00'),
            commission_rate=Decimal('10.00')
        )
    
    def test_vendor_stats_api_with_vendor_name(self):
        """Test vendor stats API endpoint using vendor_name"""
        self.client.force_authenticate(user=self.vendor)
        
        url = reverse('vendor_stats')
        response = self.client.get(url, {'vendor_name': self.vendor.username})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['vendor']['id'], self.vendor.id)
        self.assertEqual(response.data['vendor']['username'], self.vendor.username)

    def test_vendor_stats_api_with_vendor_id(self):
        """Test vendor stats API endpoint using vendor_id"""
        self.client.force_authenticate(user=self.vendor)
        
        url = reverse('vendor_stats')
        response = self.client.get(url, {'vendor_id': self.vendor.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['vendor']['id'], self.vendor.id)
    
    def test_missing_vendor_params(self):
        """Test API without vendor_id or vendor_name parameter"""
        self.client.force_authenticate(user=self.vendor)
        
        url = reverse('vendor_stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Either vendor_id or vendor_name parameter is required', response.data['message'])
    
    def test_vendor_transactions_endpoint(self):
        """Test vendor transactions API endpoint"""
        self.client.force_authenticate(user=self.vendor)
        
        url = reverse('vendor_transactions')
        response = self.client.get(url, {'vendor_id': self.vendor.id, 'period': 'this_month'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(len(response.data['transactions']), 2)
    
    def test_vendor_balance_endpoint(self):
        """Test vendor balance API endpoint"""
        self.client.force_authenticate(user=self.vendor)
        
        url = reverse('vendor_balance')
        response = self.client.get(url, {'vendor_id': self.vendor.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['balance']['wallet_balance'], 50.00)
    
    def test_vendor_earnings_list_endpoint(self):
        """Test vendor earnings list API endpoint"""
        self.client.force_authenticate(user=self.vendor)
        
        url = reverse('vendor_earnings_list')
        response = self.client.get(url, {'vendor_id': self.vendor.id, 'period': 'this_month'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(len(response.data['earnings']), 2)
    
    def test_all_vendors_stats_admin_only(self):
        """Test all vendors stats endpoint requires admin access"""
        self.client.force_authenticate(user=self.vendor)
        
        url = reverse('all_vendors_stats')
        response = self.client.get(url, {'period': 'this_month'})
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_all_vendors_stats_admin_access(self):
        """Test all vendors stats endpoint with admin access"""
        self.client.force_authenticate(user=self.admin)
        
        url = reverse('all_vendors_stats')
        response = self.client.get(url, {'period': 'this_month'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(len(response.data['vendors']), 1)
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated requests are rejected"""
        url = reverse('vendor_stats')
        response = self.client.get(url, {'vendor_id': self.vendor.id, 'period': 'this_month'})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UtilsTestCase(TestCase):
    """Test utility functions"""
    
    def test_date_range_periods(self):
        """Test different date range periods"""
        periods = ['today', 'this_week', 'this_month', 'last_month', 'this_year']
        
        for period in periods:
            start_date, end_date = get_date_range(period)
            self.assertIsNotNone(start_date)
            self.assertIsNotNone(end_date)
            self.assertLess(start_date, end_date)
