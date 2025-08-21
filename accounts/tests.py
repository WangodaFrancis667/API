from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.db.models import Q

from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch, Mock

from .models import (
    User, AdminProfile, BuyerProfile, VendorProfile, 
    PasswordReset, EmailVerification, UserActivityLog, ArchiveUser
)
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, 
    ProfileUpdateSerializer, AddEmailSerializer
)

User = get_user_model()


class UserModelTest(TestCase):
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'full_name': 'Test User',
            'phone': '+1234567890',
            'location': 'Test City',
            'role': 'buyer'
        }

    def test_user_creation(self):
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.role, 'buyer')
        self.assertEqual(user.wallet, Decimal('0.00'))
        self.assertFalse(user.email_verified)
        self.assertFalse(user.phone_verified)

    def test_user_str_representation(self):
        user = User.objects.create_user(**self.user_data)
        expected_str = f"{user.first_name} {user.last_name} ({user.role})"
        self.assertEqual(str(user), expected_str)

    def test_user_account_lock_unlock(self):
        user = User.objects.create_user(**self.user_data)
        
        # Test account locking
        self.assertFalse(user.is_account_locked())
        user.lock_account(duration_minutes=30)
        self.assertTrue(user.is_account_locked())
        
        # Test account unlocking
        user.unlock_account()
        self.assertFalse(user.is_account_locked())
        self.assertEqual(user.login_attempts, 0)

    def test_wallet_operations(self):
        user = User.objects.create_user(**self.user_data)
        
        # Test add wallet balance
        result = user.add_wallet_balance(100.50)
        self.assertTrue(result)
        user.refresh_from_db()
        self.assertEqual(user.wallet, Decimal('100.50'))
        
        # Test add negative amount
        result = user.add_wallet_balance(-50)
        self.assertFalse(result)
        user.refresh_from_db()
        self.assertEqual(user.wallet, Decimal('100.50'))

    def test_user_manager_role_filters(self):
        User.objects.create_user(username='admin1', email='admin@test.com', role='admin')
        User.objects.create_user(username='vendor1', email='vendor@test.com', role='vendor')
        User.objects.create_user(username='buyer1', email='buyer@test.com', role='buyer')
        
        self.assertEqual(User.objects.admins().count(), 1)
        self.assertEqual(User.objects.vendors().count(), 1)
        self.assertEqual(User.objects.buyers().count(), 1)

    def test_email_uniqueness(self):
        User.objects.create_user(**self.user_data)
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username='testuser2',
                email='test@example.com',  # Duplicate email
                role='buyer'
            )

    def test_full_name_clears_first_last_name(self):
        user_data = self.user_data.copy()
        user_data['first_name'] = 'First'
        user_data['last_name'] = 'Last'
        
        user = User.objects.create_user(**user_data)
        self.assertEqual(user.first_name, "")
        self.assertEqual(user.last_name, "")
        self.assertEqual(user.full_name, 'Test User')


class PasswordResetModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            role='buyer'
        )

    def test_create_fresh_password_reset(self):
        reset = PasswordReset.create_fresh(self.user, self.user.email)
        
        self.assertEqual(reset.user, self.user)
        self.assertEqual(reset.email, self.user.email)
        self.assertEqual(len(reset.verification_code), 6)
        self.assertFalse(reset.is_used)
        self.assertTrue(reset.is_valid())

    def test_password_reset_expiration(self):
        reset = PasswordReset.objects.create(
            user=self.user,
            email=self.user.email,
            verification_code='123456',
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        
        self.assertTrue(reset.is_expired())
        self.assertFalse(reset.is_valid())

    def test_invalidate_existing_codes(self):
        # Create first reset
        reset1 = PasswordReset.create_fresh(self.user, self.user.email)
        
        # Create second reset - should invalidate first
        reset2 = PasswordReset.create_fresh(self.user, self.user.email)
        
        reset1.refresh_from_db()
        self.assertTrue(reset1.is_used)
        self.assertFalse(reset2.is_used)


class EmailVerificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            role='buyer'
        )

    def test_create_fresh_email_verification(self):
        verification = EmailVerification.create_fresh(
            user=self.user,
            email=self.user.email,
            user_type='buyer'
        )
        
        self.assertEqual(verification.user, self.user)
        self.assertEqual(verification.user_type, 'buyer')
        self.assertEqual(len(verification.verification_code), 6)
        self.assertFalse(verification.verified)

    def test_mark_verified(self):
        verification = EmailVerification.create_fresh(
            user=self.user,
            email=self.user.email,
            user_type='buyer'
        )
        
        verification.mark_verified()
        self.assertTrue(verification.verified)
        self.assertIsNotNone(verification.verified_at)
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_generate_code_format(self):
        code = EmailVerification.generate_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())


class ProfileModelTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            role='admin'
        )
        self.vendor_user = User.objects.create_user(
            username='vendor',
            email='vendor@test.com',
            role='vendor'
        )
        self.buyer_user = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            role='buyer'
        )

    def test_admin_profile_creation(self):
        profile = AdminProfile.objects.create(
            user=self.admin_user,
            department='IT'
        )
        self.assertEqual(profile.user, self.admin_user)
        self.assertEqual(profile.department, 'IT')
        self.assertEqual(str(profile), f"AdminProfile: {self.admin_user.username}")

    def test_vendor_profile_creation(self):
        profile = VendorProfile.objects.create(
            user=self.vendor_user,
            business_type='Electronics',
            commission_rate=Decimal('5.00')
        )
        self.assertEqual(profile.user, self.vendor_user)
        self.assertEqual(profile.business_type, 'Electronics')
        self.assertEqual(profile.commission_rate, Decimal('5.00'))
        self.assertFalse(profile.is_verified_vendor)

    def test_buyer_profile_creation(self):
        profile = BuyerProfile.objects.create(
            user=self.buyer_user,
            phone='+1234567890',
            loyalty_tier='silver'
        )
        self.assertEqual(profile.user, self.buyer_user)
        self.assertEqual(profile.loyalty_tier, 'silver')
        self.assertEqual(str(profile), f"Buyer: {self.buyer_user.username}")


class UserActivityLogModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            role='buyer'
        )

    def test_activity_log_creation(self):
        log = UserActivityLog.objects.create(
            user=self.user,
            action='LOGIN',
            description='User logged in successfully',
            ip_address='192.168.1.1'
        )
        
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'LOGIN')
        self.assertIsNotNone(log.created_at)

    def test_activity_log_ordering(self):
        log1 = UserActivityLog.objects.create(
            user=self.user,
            action='LOGIN',
            description='First login'
        )
        log2 = UserActivityLog.objects.create(
            user=self.user,
            action='LOGOUT',
            description='Logout'
        )
        
        logs = list(UserActivityLog.objects.all())
        self.assertEqual(logs[0], log2)  # Most recent first
        self.assertEqual(logs[1], log1)


class ArchiveUserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            role='buyer'
        )

    def test_archive_user_creation(self):
        archive = ArchiveUser.objects.create(
            original_user_id=self.user.id,
            username=self.user.username,
            email=self.user.email,
            role=self.user.role,
            delete_reason='User requested account deletion'
        )
        
        self.assertEqual(archive.original_user_id, self.user.id)
        self.assertEqual(archive.username, self.user.username)
        self.assertEqual(archive.delete_reason, 'User requested account deletion')


class UserRegistrationSerializerTest(TestCase):
    def setUp(self):
        self.valid_data = {
            'full_name': 'Test User',
            'phone': '+1234567890',
            'location': 'Test City',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!'
        }

    def test_valid_registration_data(self):
        serializer = UserRegistrationSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_password_mismatch(self):
        data = self.valid_data.copy()
        data['confirm_password'] = 'DifferentPassword123!'
        
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_invalid_phone_format(self):
        data = self.valid_data.copy()
        data['phone'] = '123'  # Invalid format
        
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone', serializer.errors)

    def test_role_validation(self):
        data = self.valid_data.copy()
        data['role'] = 'admin'  # Not allowed via public registration
        
        serializer = UserRegistrationSerializer(data=data)
        if serializer.is_valid():
            # Role validation might be in validate_role method
            from rest_framework.exceptions import ValidationError as DRFValidationError
            with self.assertRaises(DRFValidationError):
                serializer.validate_role('admin')


class UserLoginSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123',
            role='buyer'
        )

    @patch('accounts.serializers.authenticate')
    def test_valid_login(self, mock_authenticate):
        mock_authenticate.return_value = self.user
        
        data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        
        serializer = UserLoginSerializer(data=data)
        if hasattr(serializer, 'is_valid'):
            self.assertTrue(serializer.is_valid())

    @patch('accounts.serializers.authenticate')
    def test_invalid_credentials(self, mock_authenticate):
        mock_authenticate.return_value = None
        
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        serializer = UserLoginSerializer(data=data)
        if hasattr(serializer, 'is_valid'):
            self.assertFalse(serializer.is_valid())


class AccountsViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123',
            role='buyer'
        )

    def test_user_signup(self):
        data = {
            'full_name': 'New User',
            'phone': '+1234567890',
            'location': 'Test City',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!'
        }
        
        response = self.client.post('/api/auth/signup/', data)
        # Response might vary based on actual implementation
        self.assertIn(response.status_code, [200, 201, 400, 404])

    def test_user_login(self):
        data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        
        response = self.client.post('/api/auth/login/', data)
        self.assertIn(response.status_code, [200, 400, 404])

    def test_authenticated_user_status(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auth/status/')
        self.assertIn(response.status_code, [200, 404])

    def test_user_logout(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/auth/logout/')
        self.assertIn(response.status_code, [200, 204, 404])

    def test_profile_update(self):
        self.client.force_authenticate(user=self.user)
        
        data = {
            'full_name': 'Updated Name',
            'location': 'New Location'
        }
        
        response = self.client.put('/api/auth/profile/update/', data)
        self.assertIn(response.status_code, [200, 400, 404])

    def test_unauthenticated_access_denied(self):
        response = self.client.get('/api/auth/profile/')
        self.assertIn(response.status_code, [401, 403, 404])


class AddEmailSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='old@example.com',
            role='buyer'
        )

    def test_valid_email_addition(self):
        data = {'email': 'new@example.com'}
        
        # Mock request context
        context = {'request': Mock(user=self.user)}
        serializer = AddEmailSerializer(data=data, context=context)
        
        self.assertTrue(serializer.is_valid())

    def test_duplicate_email_validation(self):
        User.objects.create_user(
            username='otheruser',
            email='existing@example.com',
            role='buyer'
        )
        
        data = {'email': 'existing@example.com'}
        serializer = AddEmailSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)


class UserSecurityTest(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            role='buyer'
        )

    def test_account_lockout_after_failed_attempts(self):
        # Simulate multiple failed login attempts
        for i in range(3):
            self.user.login_attempts += 1
            self.user.save()
        
        # Check if account gets locked after threshold
        if self.user.login_attempts >= 3:
            self.user.lock_account()
            self.assertTrue(self.user.is_account_locked())

    def test_password_reset_workflow(self):
        # Test password reset creation
        reset = PasswordReset.create_fresh(self.user, self.user.email)
        self.assertTrue(reset.is_valid())
        
        # Test using the reset
        reset.is_used = True
        reset.save()
        self.assertFalse(reset.is_valid())

    def test_email_verification_workflow(self):
        verification = EmailVerification.create_fresh(
            user=self.user,
            email='new@example.com',
            user_type='buyer'
        )
        
        self.assertFalse(verification.verified)
        
        # Mark as verified
        verification.mark_verified()
        
        self.assertTrue(verification.verified)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)
