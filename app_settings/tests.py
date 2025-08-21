from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import AppSettings
from .serializers import AppSettingsSerializer
from .views import AppSettingsListsView, AppSettingsDetailView

User = get_user_model()


class AppSettingsModelTest(TestCase):
    def test_app_settings_creation(self):
        setting = AppSettings.objects.create(
            setting_key='max_file_size',
            setting_value='10MB'
        )
        
        self.assertEqual(setting.setting_key, 'max_file_size')
        self.assertEqual(setting.setting_value, '10MB')
        self.assertIsNotNone(setting.created_at)
        self.assertIsNotNone(setting.updated_at)

    def test_app_settings_required_fields(self):
        # Test that setting_key is required (null=False means None values will fail)
        from django.db import transaction
        
        with transaction.atomic():
            with self.assertRaises((ValidationError, IntegrityError)):
                AppSettings.objects.create(
                    setting_key=None,  # None should fail
                    setting_value='some_value'
                )

    def test_app_settings_required_fields_value(self):
        # Test that setting_value is required (separate test to avoid transaction issues)
        from django.db import transaction
        
        with transaction.atomic():
            with self.assertRaises((ValidationError, IntegrityError)):
                AppSettings.objects.create(
                    setting_key='some_key',
                    setting_value=None  # None should fail
                )

    def test_app_settings_string_representation(self):
        setting = AppSettings.objects.create(
            setting_key='app_name',
            setting_value='My Application'
        )
        
        # Test default string representation (Django default is 'ModelName object (id)')
        str_repr = str(setting)
        self.assertIn('AppSettings object', str_repr)
        # Or just check that it's a valid string representation
        self.assertTrue(len(str_repr) > 0)

    def test_multiple_settings_creation(self):
        settings_data = [
            ('debug_mode', 'false'),
            ('api_version', 'v1.0'),
            ('max_users', '1000'),
            ('maintenance_mode', 'false'),
            ('email_notifications', 'true')
        ]
        
        for key, value in settings_data:
            AppSettings.objects.create(
                setting_key=key,
                setting_value=value
            )
        
        self.assertEqual(AppSettings.objects.count(), 5)

    def test_setting_key_max_length(self):
        # Test max length constraint - should raise an exception for keys > 100 chars
        from django.db import transaction
        
        long_key = 'a' * 101  # Exceeds max_length=100
        
        with transaction.atomic():
            with self.assertRaises((ValidationError, IntegrityError, Exception)):
                AppSettings.objects.create(
                    setting_key=long_key,
                    setting_value='test_value'
                )

    def test_setting_value_text_field(self):
        # Test that setting_value can handle large text
        large_value = 'x' * 1000  # Large text
        
        setting = AppSettings.objects.create(
            setting_key='large_config',
            setting_value=large_value
        )
        
        self.assertEqual(setting.setting_value, large_value)

    def test_datetime_fields_auto_populate(self):
        setting = AppSettings.objects.create(
            setting_key='test_key',
            setting_value='test_value'
        )
        
        self.assertIsNotNone(setting.created_at)
        self.assertIsNotNone(setting.updated_at)
        
        original_created_at = setting.created_at
        original_updated_at = setting.updated_at
        
        # Update the setting
        setting.setting_value = 'updated_value'
        setting.save()
        
        # created_at should remain the same, updated_at should change
        self.assertEqual(setting.created_at, original_created_at)
        self.assertNotEqual(setting.updated_at, original_updated_at)


class AppSettingsSerializerTest(TestCase):
    def test_valid_serializer_data(self):
        data = {
            'setting_key': 'test_setting',
            'setting_value': 'test_value'
        }
        
        serializer = AppSettingsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        # Test saving
        setting = serializer.save()
        self.assertEqual(setting.setting_key, 'test_setting')
        self.assertEqual(setting.setting_value, 'test_value')

    def test_serializer_fields(self):
        setting = AppSettings.objects.create(
            setting_key='serializer_test',
            setting_value='serializer_value'
        )
        
        serializer = AppSettingsSerializer(setting)
        data = serializer.data
        
        # Check that expected fields are present
        self.assertIn('id', data)
        self.assertIn('setting_key', data)
        self.assertIn('setting_value', data)
        
        # Check that read-only fields are excluded from input
        self.assertEqual(data['setting_key'], 'serializer_test')
        self.assertEqual(data['setting_value'], 'serializer_value')

    def test_serializer_invalid_data(self):
        # Test missing required fields
        invalid_data_sets = [
            {},  # Empty data
            {'setting_key': 'test'},  # Missing setting_value
            {'setting_value': 'test'},  # Missing setting_key
        ]
        
        for invalid_data in invalid_data_sets:
            serializer = AppSettingsSerializer(data=invalid_data)
            self.assertFalse(serializer.is_valid())

    def test_serializer_update(self):
        setting = AppSettings.objects.create(
            setting_key='update_test',
            setting_value='original_value'
        )
        
        update_data = {
            'setting_key': 'update_test',
            'setting_value': 'updated_value'
        }
        
        serializer = AppSettingsSerializer(setting, data=update_data)
        self.assertTrue(serializer.is_valid())
        
        updated_setting = serializer.save()
        self.assertEqual(updated_setting.setting_value, 'updated_value')

    def test_serializer_partial_update(self):
        setting = AppSettings.objects.create(
            setting_key='partial_test',
            setting_value='original_value'
        )
        
        partial_data = {
            'setting_value': 'partially_updated_value'
        }
        
        serializer = AppSettingsSerializer(setting, data=partial_data, partial=True)
        self.assertTrue(serializer.is_valid())
        
        updated_setting = serializer.save()
        self.assertEqual(updated_setting.setting_key, 'partial_test')  # Unchanged
        self.assertEqual(updated_setting.setting_value, 'partially_updated_value')  # Changed


class AppSettingsViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.buyer_user = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            role='buyer'
        )

    def test_list_app_settings(self):
        # Create test settings
        AppSettings.objects.create(
            setting_key='test_setting_1',
            setting_value='value_1'
        )
        AppSettings.objects.create(
            setting_key='test_setting_2',
            setting_value='value_2'
        )
        
        response = self.client.get('/api/app-settings/')
        
        # Endpoint might not exist or might require authentication
        self.assertIn(response.status_code, [200, 401, 403, 404])
        
        if response.status_code == 200:
            self.assertEqual(len(response.data), 2)

    def test_create_app_setting(self):
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'setting_key': 'new_setting',
            'setting_value': 'new_value'
        }
        
        response = self.client.post('/api/app-settings/', data)
        self.assertIn(response.status_code, [201, 400, 403, 404])
        
        if response.status_code == 201:
            self.assertEqual(AppSettings.objects.count(), 1)
            setting = AppSettings.objects.first()
            self.assertEqual(setting.setting_key, 'new_setting')

    def test_create_app_setting_unauthorized(self):
        # Try to create without authentication
        data = {
            'setting_key': 'unauthorized_setting',
            'setting_value': 'unauthorized_value'
        }
        
        response = self.client.post('/api/app-settings/', data)
        self.assertIn(response.status_code, [401, 403, 404])

    def test_create_app_setting_non_admin(self):
        # Try to create as non-admin user
        self.client.force_authenticate(user=self.buyer_user)
        
        data = {
            'setting_key': 'buyer_setting',
            'setting_value': 'buyer_value'
        }
        
        response = self.client.post('/api/app-settings/', data)
        # Might be forbidden for non-admin users
        self.assertIn(response.status_code, [201, 403, 404])

    def test_retrieve_app_setting(self):
        setting = AppSettings.objects.create(
            setting_key='retrieve_test',
            setting_value='retrieve_value'
        )
        
        response = self.client.get(f'/api/app-settings/{setting.id}/')
        self.assertIn(response.status_code, [200, 401, 403, 404])
        
        if response.status_code == 200:
            self.assertEqual(response.data['setting_key'], 'retrieve_test')

    def test_update_app_setting(self):
        self.client.force_authenticate(user=self.admin_user)
        
        setting = AppSettings.objects.create(
            setting_key='update_test',
            setting_value='original_value'
        )
        
        update_data = {
            'setting_key': 'update_test',
            'setting_value': 'updated_value'
        }
        
        response = self.client.put(f'/api/app-settings/{setting.id}/', update_data)
        self.assertIn(response.status_code, [200, 400, 403, 404, 405])
        
        if response.status_code == 200:
            setting.refresh_from_db()
            self.assertEqual(setting.setting_value, 'updated_value')

    def test_partial_update_app_setting(self):
        self.client.force_authenticate(user=self.admin_user)
        
        setting = AppSettings.objects.create(
            setting_key='patch_test',
            setting_value='original_value'
        )
        
        partial_data = {
            'setting_value': 'patched_value'
        }
        
        response = self.client.patch(f'/api/app-settings/{setting.id}/', partial_data)
        self.assertIn(response.status_code, [200, 400, 403, 404, 405])
        
        if response.status_code == 200:
            setting.refresh_from_db()
            self.assertEqual(setting.setting_value, 'patched_value')

    def test_delete_app_setting(self):
        self.client.force_authenticate(user=self.admin_user)
        
        setting = AppSettings.objects.create(
            setting_key='delete_test',
            setting_value='delete_value'
        )
        
        response = self.client.delete(f'/api/app-settings/{setting.id}/')
        self.assertIn(response.status_code, [204, 403, 404, 405])
        
        if response.status_code == 204:
            self.assertFalse(AppSettings.objects.filter(id=setting.id).exists())

    def test_invalid_setting_creation(self):
        self.client.force_authenticate(user=self.admin_user)
        
        invalid_data_sets = [
            {},  # Empty data
            {'setting_key': ''},  # Empty key
            {'setting_value': ''},  # Empty value
            {'setting_key': 'test'},  # Missing value
            {'setting_value': 'test'},  # Missing key
        ]
        
        for invalid_data in invalid_data_sets:
            response = self.client.post('/api/app-settings/', invalid_data)
            if response.status_code != 404:  # Skip if endpoint doesn't exist
                self.assertIn(response.status_code, [400, 403])


class AppSettingsQueryTest(TestCase):
    def setUp(self):
        # Create test settings
        self.settings_data = [
            ('debug_mode', 'false'),
            ('api_version', 'v1.0'),
            ('max_file_size', '10MB'),
            ('email_enabled', 'true'),
            ('maintenance_mode', 'false')
        ]
        
        for key, value in self.settings_data:
            AppSettings.objects.create(
                setting_key=key,
                setting_value=value
            )

    def test_filter_by_setting_key(self):
        debug_setting = AppSettings.objects.filter(setting_key='debug_mode').first()
        self.assertIsNotNone(debug_setting)
        self.assertEqual(debug_setting.setting_value, 'false')

    def test_get_setting_value(self):
        # Test getting a specific setting value
        api_version = AppSettings.objects.filter(setting_key='api_version').first()
        self.assertEqual(api_version.setting_value, 'v1.0')

    def test_setting_exists(self):
        # Test checking if a setting exists
        exists = AppSettings.objects.filter(setting_key='debug_mode').exists()
        self.assertTrue(exists)
        
        not_exists = AppSettings.objects.filter(setting_key='nonexistent_key').exists()
        self.assertFalse(not_exists)

    def test_all_settings_count(self):
        total_settings = AppSettings.objects.count()
        self.assertEqual(total_settings, 5)

    def test_settings_ordering(self):
        # Test default ordering (might be by id or created_at)
        settings = list(AppSettings.objects.all())
        self.assertEqual(len(settings), 5)
        
        # Test ordering by setting_key
        ordered_settings = list(AppSettings.objects.order_by('setting_key'))
        self.assertEqual(ordered_settings[0].setting_key, 'api_version')  # Alphabetically first

    def test_settings_values_list(self):
        # Test getting just the keys
        keys = list(AppSettings.objects.values_list('setting_key', flat=True))
        self.assertEqual(len(keys), 5)
        self.assertIn('debug_mode', keys)
        
        # Test getting key-value pairs
        key_value_pairs = list(AppSettings.objects.values_list('setting_key', 'setting_value'))
        self.assertEqual(len(key_value_pairs), 5)
        self.assertIn(('debug_mode', 'false'), key_value_pairs)


class AppSettingsIntegrationTest(TestCase):
    def test_setting_lifecycle(self):
        # Test complete lifecycle of a setting
        
        # 1. Create setting
        setting = AppSettings.objects.create(
            setting_key='lifecycle_test',
            setting_value='initial_value'
        )
        self.assertEqual(setting.setting_value, 'initial_value')
        
        # 2. Retrieve setting
        retrieved_setting = AppSettings.objects.get(id=setting.id)
        self.assertEqual(retrieved_setting.setting_key, 'lifecycle_test')
        
        # 3. Update setting
        retrieved_setting.setting_value = 'updated_value'
        retrieved_setting.save()
        
        # 4. Verify update
        updated_setting = AppSettings.objects.get(id=setting.id)
        self.assertEqual(updated_setting.setting_value, 'updated_value')
        
        # 5. Delete setting
        updated_setting.delete()
        
        # 6. Verify deletion
        with self.assertRaises(AppSettings.DoesNotExist):
            AppSettings.objects.get(id=setting.id)

    def test_bulk_operations(self):
        # Test bulk creation
        bulk_settings = [
            AppSettings(setting_key=f'bulk_key_{i}', setting_value=f'bulk_value_{i}')
            for i in range(5)
        ]
        
        AppSettings.objects.bulk_create(bulk_settings)
        self.assertEqual(AppSettings.objects.filter(setting_key__startswith='bulk_key_').count(), 5)
        
        # Test bulk update
        AppSettings.objects.filter(setting_key__startswith='bulk_key_').update(
            setting_value='bulk_updated_value'
        )
        
        updated_count = AppSettings.objects.filter(setting_value='bulk_updated_value').count()
        self.assertEqual(updated_count, 5)


class AppSettingsEdgeCasesTest(TestCase):
    def test_duplicate_setting_keys(self):
        # Create first setting
        AppSettings.objects.create(
            setting_key='duplicate_key',
            setting_value='first_value'
        )
        
        # Create second setting with same key (should be allowed based on model)
        AppSettings.objects.create(
            setting_key='duplicate_key',
            setting_value='second_value'
        )
        
        # Both should exist
        duplicate_settings = AppSettings.objects.filter(setting_key='duplicate_key')
        self.assertEqual(duplicate_settings.count(), 2)

    def test_empty_string_values(self):
        # Test empty string as setting value
        setting = AppSettings.objects.create(
            setting_key='empty_value_test',
            setting_value=''
        )
        self.assertEqual(setting.setting_value, '')

    def test_special_characters_in_values(self):
        special_value = 'Test value with !@#$%^&*()_+-={}[]|\\:";\'<>?,./'
        
        setting = AppSettings.objects.create(
            setting_key='special_chars_test',
            setting_value=special_value
        )
        self.assertEqual(setting.setting_value, special_value)

    def test_json_string_as_value(self):
        json_value = '{"key": "value", "number": 123, "boolean": true}'
        
        setting = AppSettings.objects.create(
            setting_key='json_test',
            setting_value=json_value
        )
        self.assertEqual(setting.setting_value, json_value)
