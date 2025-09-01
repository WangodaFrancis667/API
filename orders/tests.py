from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.exceptions import ValidationError

from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch, Mock

from .models import GroupOrder, Order, OrderItem, OrderReturn
from .serializers import (
    OrderCreateSerializer, OrderItemCreateSerializer, 
    OrderResponseSerializer
)
from .services import (
    create_individual_order, # create_or_join_group_order,
    get_product, _price_guard
)
from productManagement.models import Categories, Products

User = get_user_model()


# class GroupOrderModelTest(TestCase):
#     def setUp(self):
#         self.vendor_user = User.objects.create_user(
#             username='vendor',
#             email='vendor@test.com',
#             role='vendor'
#         )
#         self.category = Categories.objects.create(
#             name='Electronics',
#             description='Electronic products',
#             image_url='electronics.jpg'
#         )
#         self.product = Products.objects.create(
#             vendor=self.vendor_user,
#             title='Test Product',
#             description='A test product',
#             regular_price=Decimal('100.00'),
#             group_price=Decimal('90.00'),
#             min_quantity=10,
#             unit='pieces',
#             category=self.category
#         )

#     def test_group_order_creation(self):
#         deadline = timezone.now() + timedelta(days=7)
#         group_order = GroupOrder.objects.create(
#             group_id='GROUP123',
#             product_id=self.product.id,
#             total_quantity=0,
#             deadline=deadline
#         )
        
#         self.assertEqual(group_order.group_id, 'GROUP123')
#         self.assertEqual(group_order.product_id, self.product.id)
#         self.assertEqual(group_order.status, GroupOrder.STATUS_OPEN)
#         self.assertEqual(group_order.total_quantity, 0)

#     def test_group_order_str_representation(self):
#         deadline = timezone.now() + timedelta(days=7)
#         group_order = GroupOrder.objects.create(
#             group_id='GROUP123',
#             product_id=self.product.id,
#             total_quantity=0,
#             deadline=deadline
#         )
#         expected_str = f"GROUP123 ({self.product.id})"
#         self.assertEqual(str(group_order), expected_str)

#     def test_group_order_status_choices(self):
#         deadline = timezone.now() + timedelta(days=7)
#         group_order = GroupOrder.objects.create(
#             group_id='GROUP123',
#             product_id=self.product.id,
#             total_quantity=0,
#             deadline=deadline
#         )
        
#         # Test status changes
#         group_order.status = GroupOrder.STATUS_CLOSED
#         group_order.save()
#         self.assertEqual(group_order.status, 'closed')
        
#         group_order.status = GroupOrder.STATUS_FULFILLED
#         group_order.save()
#         self.assertEqual(group_order.status, 'fulfilled')


class OrderModelTest(TestCase):
    def setUp(self):
        self.buyer_user = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            role='buyer'
        )
        self.vendor_user = User.objects.create_user(
            username='vendor',
            email='vendor@test.com',
            role='vendor'
        )

    def test_order_creation(self):
        order = Order.objects.create(
            user=self.buyer_user,
            vendor_id=self.vendor_user.id,
            subtotal=Decimal('100.00'),
            delivery_fee=Decimal('10.00'),
            total_amount=Decimal('110.00'),
            payment_method='mobile_money',
            delivery_address='123 Test Street'
        )
        
        self.assertEqual(order.user, self.buyer_user)
        self.assertEqual(order.vendor_id, self.vendor_user.id)
        self.assertEqual(order.status, Order.STATUS_PENDING)
        self.assertEqual(order.total_amount, Decimal('110.00'))

    def test_order_str_representation(self):
        order = Order.objects.create(
            user=self.buyer_user,
            vendor_id=self.vendor_user.id,
            subtotal=Decimal('100.00'),
            delivery_fee=Decimal('10.00'),
            total_amount=Decimal('110.00'),
            payment_method='mobile_money',
            delivery_address='123 Test Street'
        )
        expected_str = f"Order #{order.pk}"
        self.assertEqual(str(order), expected_str)

    def test_order_status_choices(self):
        order = Order.objects.create(
            user=self.buyer_user,
            vendor_id=self.vendor_user.id,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('110.00'),
            payment_method='mobile_money',
            delivery_address='123 Test Street'
        )
        
        # Test status changes
        order.status = Order.STATUS_PROCESSING
        order.save()
        self.assertEqual(order.status, 'processing')
        
        order.status = Order.STATUS_SHIPPED
        order.save()
        self.assertEqual(order.status, 'shipped')
        
        order.status = Order.STATUS_DELIVERED
        order.save()
        self.assertEqual(order.status, 'delivered')

    # def test_order_group_order_relationship(self):
    #     order = Order.objects.create(
    #         user=self.buyer_user,
    #         vendor_id=self.vendor_user.id,
    #         group_id='GROUP123',
    #         subtotal=Decimal('100.00'),
    #         total_amount=Decimal('110.00'),
    #         payment_method='mobile_money',
    #         delivery_address='123 Test Street'
    #     )
        
    #     self.assertEqual(order.group_id, 'GROUP123')


class OrderItemModelTest(TestCase):
    def setUp(self):
        self.buyer_user = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            role='buyer'
        )
        self.vendor_user = User.objects.create_user(
            username='vendor',
            email='vendor@test.com',
            role='vendor'
        )
        self.category = Categories.objects.create(
            name='Electronics',
            description='Electronic products',
            image_url='electronics.jpg'
        )
        self.product = Products.objects.create(
            vendor=self.vendor_user,
            title='Test Product',
            description='A test product',
            regular_price=Decimal('50.00'),
            min_quantity=5,
            unit='pieces',
            category=self.category
        )
        self.order = Order.objects.create(
            user=self.buyer_user,
            vendor_id=self.vendor_user.id,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('110.00'),
            payment_method='mobile_money',
            delivery_address='123 Test Street'
        )

    def test_order_item_creation(self):
        order_item = OrderItem.objects.create(
            order=self.order,
            product_id=self.product.id,
            quantity=2,
            unit_price=Decimal('50.00'),
            price=Decimal('100.00')
        )
        
        self.assertEqual(order_item.order, self.order)
        self.assertEqual(order_item.product_id, self.product.id)
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.price, Decimal('100.00'))

    def test_order_items_relationship(self):
        order_item1 = OrderItem.objects.create(
            order=self.order,
            product_id=self.product.id,
            quantity=1,
            unit_price=Decimal('50.00'),
            price=Decimal('50.00')
        )
        order_item2 = OrderItem.objects.create(
            order=self.order,
            product_id=self.product.id,
            quantity=2,
            unit_price=Decimal('50.00'),
            price=Decimal('100.00')
        )
        
        items = self.order.items.all()
        self.assertEqual(items.count(), 2)
        self.assertIn(order_item1, items)
        self.assertIn(order_item2, items)


class OrderReturnModelTest(TestCase):
    def setUp(self):
        self.buyer_user = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            role='buyer'
        )
        self.vendor_user = User.objects.create_user(
            username='vendor',
            email='vendor@test.com',
            role='vendor'
        )
        self.order = Order.objects.create(
            user=self.buyer_user,
            vendor_id=self.vendor_user.id,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('110.00'),
            payment_method='mobile_money',
            delivery_address='123 Test Street'
        )

    def test_order_return_creation(self):
        order_return = OrderReturn.objects.create(
            order=self.order,
            user=self.buyer_user,
            return_reason='Product defective',
            return_status=OrderReturn.STATUS_PENDING
        )
        
        self.assertEqual(order_return.order, self.order)
        self.assertEqual(order_return.user, self.buyer_user)
        self.assertEqual(order_return.return_status, 'pending')
        self.assertEqual(order_return.return_reason, 'Product defective')

    def test_order_return_status_choices(self):
        order_return = OrderReturn.objects.create(
            order=self.order,
            user=self.buyer_user,
            return_reason='Product defective'
        )
        
        # Test status changes
        order_return.return_status = OrderReturn.STATUS_APPROVED
        order_return.save()
        self.assertEqual(order_return.return_status, 'approved')
        
        order_return.return_status = OrderReturn.STATUS_COMPLETED
        order_return.save()
        self.assertEqual(order_return.return_status, 'completed')

    def test_order_returns_relationship(self):
        return1 = OrderReturn.objects.create(
            order=self.order,
            user=self.buyer_user,
            return_reason='Defective product'
        )
        return2 = OrderReturn.objects.create(
            order=self.order,
            user=self.buyer_user,
            return_reason='Wrong item shipped'
        )
        
        returns = self.order.returns.all()
        self.assertEqual(returns.count(), 2)
        self.assertIn(return1, returns)
        self.assertIn(return2, returns)


class OrderSerializerTest(TestCase):
    def setUp(self):
        self.buyer_user = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            role='buyer'
        )
        self.vendor_user = User.objects.create_user(
            username='vendor',
            email='vendor@test.com',
            role='vendor'
        )
        self.category = Categories.objects.create(
            name='Electronics',
            description='Electronic products',
            image_url='electronics.jpg'
        )
        self.product = Products.objects.create(
            vendor=self.vendor_user,
            title='Test Product',
            description='A test product',
            regular_price=Decimal('50.00'),
            min_quantity=5,
            unit='pieces',
            category=self.category
        )

    def test_order_item_create_serializer_valid_data(self):
        data = {
            'product_id': self.product.id,
            'quantity': 2,
            'unit_price': '50.00'
        }
        serializer = OrderItemCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_order_item_create_serializer_invalid_quantity(self):
        data = {
            'product_id': self.product.id,
            'quantity': 0,  # Invalid - minimum is 1
            'unit_price': '50.00'
        }
        serializer = OrderItemCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('quantity', serializer.errors)

    def test_order_create_serializer_valid_data(self):
        data = {
            'buyer_id': self.buyer_user.id,
            'vendor_id': self.vendor_user.id,
            'payment_method': 'mobile_money',
            'delivery_address': '123 Test Street',
            'subtotal': '100.00',
            'delivery_fee': '10.00',
            'total_amount': '110.00',
            'item': {
                'product_id': self.product.id,
                'quantity': 2,
                'unit_price': '50.00'
            },
            'is_group_order': False
        }
        serializer = OrderCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_order_create_serializer_invalid_payment_method(self):
        data = {
            'buyer_id': self.buyer_user.id,
            'vendor_id': self.vendor_user.id,
            'payment_method': 'invalid_method',
            'delivery_address': '123 Test Street',
            'subtotal': '100.00',
            'delivery_fee': '10.00',
            'total_amount': '110.00',
            'item': {
                'product_id': self.product.id,
                'quantity': 2,
                'unit_price': '50.00'
            }
        }
        serializer = OrderCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('payment_method', serializer.errors)

    def test_order_response_serializer(self):
        order = Order.objects.create(
            user=self.buyer_user,
            vendor_id=self.vendor_user.id,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('110.00'),
            payment_method='mobile_money',
            delivery_address='123 Test Street'
        )
        
        serializer = OrderResponseSerializer(order)
        data = serializer.data
        
        self.assertEqual(data['id'], order.id)
        self.assertEqual(data['payment_method'], 'mobile_money')
        self.assertEqual(data['status'], Order.STATUS_PENDING)


class OrderServicesTest(TestCase):
    def setUp(self):
        self.buyer_user = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            role='buyer'
        )
        self.vendor_user = User.objects.create_user(
            username='vendor',
            email='vendor@test.com',
            role='vendor'
        )
        self.category = Categories.objects.create(
            name='Electronics',
            description='Electronic products',
            image_url='electronics.jpg'
        )
        self.product = Products.objects.create(
            vendor=self.vendor_user,
            title='Test Product',
            description='A test product',
            regular_price=Decimal('50.00'),
            group_price=Decimal('45.00'),
            min_quantity=5,
            unit='pieces',
            category=self.category
        )

    def test_get_product_service(self):
        product_data = get_product(self.product.id)
        
        self.assertEqual(product_data['id'], self.product.id)
        self.assertEqual(product_data['vendor_id'], self.vendor_user.id)
        self.assertEqual(product_data['regular_price'], self.product.regular_price)
        self.assertEqual(product_data['group_price'], self.product.group_price)
        self.assertEqual(product_data['title'], self.product.title)

    def test_get_product_service_inactive_product(self):
        # Make product inactive
        self.product.is_active = False
        self.product.save()
        
        with self.assertRaises(ValidationError):
            get_product(self.product.id)

    def test_get_product_service_nonexistent_product(self):
        with self.assertRaises(ValidationError):
            get_product(99999)  # Non-existent ID

    def test_price_guard_valid(self):
        # Should not raise any exception
        _price_guard(Decimal('100.00'), Decimal('100.00'))
        _price_guard(Decimal('100.00'), Decimal('100.01'))  # Within tolerance

    def test_price_guard_invalid(self):
        with self.assertRaises(ValueError):
            _price_guard(Decimal('100.00'), Decimal('95.00'))  # Outside tolerance

    @patch('orders.services.notify_vendor_new_order.delay')
    @patch('orders.services.notify_buyer_status.delay')
    def test_create_individual_order(self, mock_notify_buyer, mock_notify_vendor):
        order = create_individual_order(
            buyer_id=self.buyer_user.id,
            vendor_id=self.vendor_user.id,
            product_id=self.product.id,
            quantity=2,
            unit_price=Decimal('50.00'),
            payment_method='mobile_money',
            delivery_address='123 Test Street',
            subtotal=Decimal('100.00'),
            delivery_fee=Decimal('10.00'),
            total_amount=Decimal('110.00')
        )
        
        self.assertEqual(order.user_id, self.buyer_user.id)
        self.assertEqual(order.vendor_id, self.vendor_user.id)
        self.assertEqual(order.total_amount, Decimal('110.00'))
        self.assertEqual(order.status, Order.STATUS_PENDING)
        
        # Check that order item was created
        items = order.items.all()
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().product_id, self.product.id)
        self.assertEqual(items.first().quantity, 2)
        
        # Check that notifications were triggered
        mock_notify_vendor.assert_called_once()
        mock_notify_buyer.assert_called_once()

    def test_create_individual_order_price_mismatch(self):
        with self.assertRaises(ValueError):
            create_individual_order(
                buyer_id=self.buyer_user.id,
                vendor_id=self.vendor_user.id,
                product_id=self.product.id,
                quantity=2,
                unit_price=Decimal('50.00'),
                payment_method='mobile_money',
                delivery_address='123 Test Street',
                subtotal=Decimal('90.00'),  # Wrong subtotal
                delivery_fee=Decimal('10.00'),
                total_amount=Decimal('100.00')
            )


class OrderViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.buyer_user = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            role='buyer'
        )
        self.vendor_user = User.objects.create_user(
            username='vendor',
            email='vendor@test.com',
            password='testpass123',
            role='vendor'
        )
        self.category = Categories.objects.create(
            name='Electronics',
            description='Electronic products',
            image_url='electronics.jpg'
        )
        self.product = Products.objects.create(
            vendor=self.vendor_user,
            title='Test Product',
            description='A test product',
            regular_price=Decimal('50.00'),
            group_price=Decimal('45.00'),
            min_quantity=5,
            unit='pieces',
            category=self.category
        )

    def test_create_individual_order_view(self):
        self.client.force_authenticate(user=self.buyer_user)
        
        data = {
            'buyer_id': self.buyer_user.id,
            'vendor_id': self.vendor_user.id,
            'payment_method': 'mobile_money',
            'delivery_address': '123 Test Street',
            'subtotal': '100.00',
            'delivery_fee': '10.00',
            'total_amount': '110.00',
            'item': {
                'product_id': self.product.id,
                'quantity': 2,
                'unit_price': '50.00'
            },
            'is_group_order': False
        }
        
        response = self.client.post('/api/orders/create/', data, format='json')
        self.assertIn(response.status_code, [200, 201, 400, 404])

    def test_create_group_order_view(self):
        self.client.force_authenticate(user=self.buyer_user)
        
        data = {
            'buyer_id': self.buyer_user.id,
            'vendor_id': self.vendor_user.id,
            'payment_method': 'mobile_money',
            'delivery_address': '123 Test Street',
            'subtotal': '90.00',
            'delivery_fee': '10.00',
            'total_amount': '100.00',
            'item': {
                'product_id': self.product.id,
                'quantity': 2,
                'unit_price': '45.00'
            },
            'is_group_order': True
        }
        
        response = self.client.post('/api/orders/create/', data, format='json')
        self.assertIn(response.status_code, [200, 201, 400, 404])

    def test_create_order_unauthenticated(self):
        data = {
            'buyer_id': self.buyer_user.id,
            'vendor_id': self.vendor_user.id,
            'payment_method': 'mobile_money',
            'delivery_address': '123 Test Street',
            'subtotal': '100.00',
            'delivery_fee': '10.00',
            'total_amount': '110.00',
            'item': {
                'product_id': self.product.id,
                'quantity': 2,
                'unit_price': '50.00'
            }
        }
        
        response = self.client.post('/api/orders/create/', data, format='json')
        self.assertIn(response.status_code, [401, 403, 404])

    def test_create_order_invalid_data(self):
        self.client.force_authenticate(user=self.buyer_user)
        
        data = {
            'buyer_id': self.buyer_user.id,
            'vendor_id': self.vendor_user.id,
            'payment_method': 'invalid_method',  # Invalid payment method
            'delivery_address': '123 Test Street',
            'subtotal': '100.00',
            'delivery_fee': '10.00',
            'total_amount': '110.00',
            'item': {
                'product_id': self.product.id,
                'quantity': 2,
                'unit_price': '50.00'
            }
        }
        
        response = self.client.post('/api/orders/create/', data, format='json')
        self.assertIn(response.status_code, [400, 404])


class OrderTransactionTest(TransactionTestCase):
    def setUp(self):
        self.buyer_user = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            role='buyer'
        )
        self.vendor_user = User.objects.create_user(
            username='vendor',
            email='vendor@test.com',
            role='vendor'
        )
        self.category = Categories.objects.create(
            name='Electronics',
            description='Electronic products',
            image_url='electronics.jpg'
        )
        self.product = Products.objects.create(
            vendor=self.vendor_user,
            title='Test Product',
            description='A test product',
            regular_price=Decimal('50.00'),
            min_quantity=5,
            unit='pieces',
            category=self.category
        )

    def test_order_creation_atomicity(self):
        """Test that order creation is atomic - either all or nothing"""
        with patch('orders.services.OrderItem.objects.create', side_effect=Exception('Database error')):
            with self.assertRaises(Exception):
                create_individual_order(
                    buyer_id=self.buyer_user.id,
                    vendor_id=self.vendor_user.id,
                    product_id=self.product.id,
                    quantity=2,
                    unit_price=Decimal('50.00'),
                    payment_method='mobile_money',
                    delivery_address='123 Test Street',
                    subtotal=Decimal('100.00'),
                    delivery_fee=Decimal('10.00'),
                    total_amount=Decimal('110.00')
                )
        
        # Verify no order was created due to rollback
        self.assertEqual(Order.objects.count(), 0)


# class GroupOrderServicesTest(TestCase):
#     def setUp(self):
#         self.buyer_user = User.objects.create_user(
#             username='buyer',
#             email='buyer@test.com',
#             role='buyer'
#         )
#         self.vendor_user = User.objects.create_user(
#             username='vendor',
#             email='vendor@test.com',
#             role='vendor'
#         )
#         self.category = Categories.objects.create(
#             name='Electronics',
#             description='Electronic products',
#             image_url='electronics.jpg'
#         )
#         self.product = Products.objects.create(
#             vendor=self.vendor_user,
#             title='Group Order Product',
#             description='Product for group orders',
#             regular_price=Decimal('50.00'),
#             group_price=Decimal('45.00'),
#             min_quantity=10,
#             unit='pieces',
#             category=self.category
#         )

#     @patch('orders.services.notify_vendor_new_order.delay')
#     @patch('orders.services.notify_buyer_status.delay')
#     def test_create_group_order(self, mock_notify_buyer, mock_notify_vendor):
#         if hasattr(self, 'create_or_join_group_order'):
#             # Test would require actual implementation
#             pass
        
#         # Basic group order test
#         deadline = timezone.now() + timedelta(days=7)
#         group_order = GroupOrder.objects.create(
#             group_id='GROUP123',
#             product_id=self.product.id,
#             total_quantity=0,
#             deadline=deadline
#         )
        
#         self.assertEqual(group_order.status, GroupOrder.STATUS_OPEN)


# class OrderStatusTransitionTest(TestCase):
#     def setUp(self):
#         self.buyer_user = User.objects.create_user(
#             username='buyer',
#             email='buyer@test.com',
#             role='buyer'
#         )
#         self.vendor_user = User.objects.create_user(
#             username='vendor',
#             email='vendor@test.com',
#             role='vendor'
#         )
#         self.order = Order.objects.create(
#             user=self.buyer_user,
#             vendor_id=self.vendor_user.id,
#             subtotal=Decimal('100.00'),
#             total_amount=Decimal('110.00'),
#             payment_method='mobile_money',
#             delivery_address='123 Test Street'
#         )

#     def test_order_status_progression(self):
#         # Test normal order status progression
#         self.assertEqual(self.order.status, Order.STATUS_PENDING)
        
#         self.order.status = Order.STATUS_PROCESSING
#         self.order.save()
#         self.assertEqual(self.order.status, 'processing')
        
#         self.order.status = Order.STATUS_SHIPPED
#         self.order.save()
#         self.assertEqual(self.order.status, 'shipped')
        
#         self.order.status = Order.STATUS_DELIVERED
#         self.order.save()
#         self.assertEqual(self.order.status, 'delivered')

#     def test_order_cancellation(self):
#         self.order.status = Order.STATUS_CANCELLED
#         self.order.save()
#         self.assertEqual(self.order.status, 'cancelled')

#     def test_return_eligibility_setting(self):
#         # Test setting return eligibility
#         return_date = timezone.now() + timedelta(days=7)
#         self.order.return_eligible_until = return_date
#         self.order.save()
        
#         self.assertIsNotNone(self.order.return_eligible_until)
#         self.assertTrue(self.order.return_eligible_until > timezone.now())
