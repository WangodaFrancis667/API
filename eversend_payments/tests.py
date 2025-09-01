import json
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Transaction, Wallet, Commission, Payment, Earning, AuditLog
from .services.eversend import get_eversend_token, EversendAPIError
from .utils import update_wallet_amount, validate_currency, validate_amount
from .validators import verify_webhook, validate_eversend_payload


class EversendModelsTestCase(TestCase):
    """Test cases for Eversend payment models"""

    def setUp(self):
        self.transaction_data = {
            "uuid": "test-user-123",
            "transaction_ref": "txn_test123",
            "currency": "USD",
            "amount": Decimal("100.00"),
            "service_fee": Decimal("5.00"),
            "transaction_type": "deposit",
            "status": "pending",
        }

    def test_transaction_creation(self):
        """Test transaction model creation"""
        transaction = Transaction.objects.create(**self.transaction_data)

        self.assertEqual(transaction.uuid, "test-user-123")
        self.assertEqual(transaction.currency, "USD")
        self.assertEqual(transaction.amount, Decimal("100.00"))
        self.assertEqual(transaction.status, "pending")
        self.assertEqual(
            str(transaction), f"{transaction.transaction_ref} ({transaction.status})"
        )

    def test_wallet_creation(self):
        """Test wallet model creation"""
        wallet = Wallet.objects.create(
            uuid="test-user-123", currency="USD", amount=Decimal("500.00")
        )

        self.assertEqual(wallet.uuid, "test-user-123")
        self.assertEqual(wallet.currency, "USD")
        self.assertEqual(wallet.amount, Decimal("500.00"))

    def test_wallet_unique_constraint(self):
        """Test wallet unique constraint on uuid and currency"""
        Wallet.objects.create(
            uuid="test-user-123", currency="USD", amount=Decimal("100.00")
        )

        # This should not create a duplicate
        with self.assertRaises(Exception):
            Wallet.objects.create(
                uuid="test-user-123", currency="USD", amount=Decimal("200.00")
            )

    def test_earning_creation(self):
        """Test earning model creation"""
        earning = Earning.objects.create(
            uuid="test-user-123",
            currency="USD",
            transaction_ref="txn_test123",
            service_name="exchange",
            amount=Decimal("10.00"),
            status="completed",
        )

        self.assertEqual(earning.uuid, "test-user-123")
        self.assertEqual(earning.amount, Decimal("10.00"))
        self.assertEqual(earning.status, "completed")


class EversendUtilsTestCase(TestCase):
    """Test cases for utility functions"""

    def setUp(self):
        self.wallet = Wallet.objects.create(
            uuid="test-user-123", currency="USD", amount=Decimal("100.00")
        )

    def test_validate_currency_valid(self):
        """Test currency validation with valid currencies"""
        self.assertTrue(validate_currency("USD"))
        self.assertTrue(validate_currency("EUR"))
        self.assertTrue(validate_currency("GBP"))

    def test_validate_currency_invalid(self):
        """Test currency validation with invalid currencies"""
        self.assertFalse(validate_currency("US"))  # Too short
        self.assertFalse(validate_currency("USDD"))  # Too long
        self.assertFalse(validate_currency("usd"))  # Lowercase
        self.assertFalse(validate_currency("123"))  # Numbers
        self.assertFalse(validate_currency(""))  # Empty

    def test_validate_amount_valid(self):
        """Test amount validation with valid amounts"""
        self.assertEqual(validate_amount("100.50"), Decimal("100.50"))
        self.assertEqual(validate_amount(100), Decimal("100"))
        self.assertEqual(validate_amount(0.01), Decimal("0.01"))

    def test_validate_amount_invalid(self):
        """Test amount validation with invalid amounts"""
        self.assertIsNone(validate_amount(0))
        self.assertIsNone(validate_amount(-10))
        self.assertIsNone(validate_amount("invalid"))
        self.assertIsNone(validate_amount(None))

    def test_update_wallet_amount_credit(self):
        """Test crediting wallet amount"""
        result = update_wallet_amount(
            uuid="test-user-123", currency="USD", amount=Decimal("50.00"), is_add=True
        )

        self.assertTrue(result)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.amount, Decimal("150.00"))

    def test_update_wallet_amount_debit(self):
        """Test debiting wallet amount"""
        result = update_wallet_amount(
            uuid="test-user-123", currency="USD", amount=Decimal("30.00"), is_add=False
        )

        self.assertTrue(result)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.amount, Decimal("70.00"))

    def test_update_wallet_amount_insufficient_balance(self):
        """Test debiting more than available balance"""
        result = update_wallet_amount(
            uuid="test-user-123", currency="USD", amount=Decimal("150.00"), is_add=False
        )

        self.assertFalse(result)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.amount, Decimal("100.00"))  # Unchanged


class EversendValidatorsTestCase(TestCase):
    """Test cases for validators"""

    @override_settings(EVERSEND_WEBHOOK_SECRET="test-secret")
    def test_verify_webhook_valid_signature(self):
        """Test webhook verification with valid signature"""
        import hmac
        import hashlib

        payload = (
            b'{"eventType": "wallet.load.successful", "transactionRef": "test123"}'
        )
        secret = "test-secret"

        signature = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()

        headers = {"x-eversend-signature": f"sha256={signature}"}

        self.assertTrue(verify_webhook(headers, payload))

    def test_verify_webhook_invalid_signature(self):
        """Test webhook verification with invalid signature"""
        payload = b'{"eventType": "wallet.load.successful"}'
        headers = {"x-eversend-signature": "invalid-signature"}

        with override_settings(EVERSEND_WEBHOOK_SECRET="test-secret"):
            self.assertFalse(verify_webhook(headers, payload))

    def test_validate_eversend_payload_valid(self):
        """Test payload validation with valid data"""
        payload = {
            "eventType": "wallet.load.successful",
            "transactionRef": "txn_12345",
            "amount": 100.00,
        }

        is_valid, error = validate_eversend_payload(payload)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_validate_eversend_payload_invalid(self):
        """Test payload validation with invalid data"""
        payload = {"eventType": "invalid.event", "transactionRef": "123"}  # Too short

        is_valid, error = validate_eversend_payload(payload)
        self.assertFalse(is_valid)
        self.assertIn("Invalid eventType", error)


class EversendServiceTestCase(TestCase):
    """Test cases for Eversend service functions"""

    @patch("eversend_payments.services.eversend.requests.get")
    @override_settings(
        EVERSEND_CLIENT_ID="test-id", EVERSEND_CLIENT_SECRET="test-secret"
    )
    def test_get_eversend_token_success(self, mock_get):
        """Test successful token retrieval"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "test-access-token"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        token = get_eversend_token()
        self.assertEqual(token, "test-access-token")

    @patch("eversend_payments.services.eversend.requests.get")
    def test_get_eversend_token_failure(self, mock_get):
        """Test failed token retrieval"""
        mock_get.side_effect = Exception("Network error")

        token = get_eversend_token()
        self.assertIsNone(token)


class EversendAPITestCase(APITestCase):
    """Test cases for API endpoints"""

    def setUp(self):
        self.webhook_url = reverse("eversend-webhook")
        self.token_url = reverse("eversend-token")

    @patch("eversend_payments.views.get_eversend_token")
    def test_token_endpoint_success(self, mock_get_token):
        """Test successful token endpoint"""
        mock_get_token.return_value = "test-token"

        response = self.client.get(self.token_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    @patch("eversend_payments.views.get_eversend_token")
    def test_token_endpoint_failure(self, mock_get_token):
        """Test failed token endpoint"""
        mock_get_token.return_value = None

        response = self.client.get(self.token_url)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    @override_settings(EVERSEND_WEBHOOK_SECRET="")
    def test_webhook_endpoint_success(self):
        """Test successful webhook processing"""
        # Create a transaction to be updated
        Transaction.objects.create(
            uuid="test-user-123",
            transaction_ref="txn_test123",
            currency="USD",
            amount=Decimal("100.00"),
            status="pending",
        )

        payload = {
            "eventType": "wallet.load.successful",
            "transactionRef": "txn_test123",
            "status": "successful",
            "amount": 100.00,
            "currency": "USD",
        }

        response = self.client.post(
            self.webhook_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if transaction was updated
        transaction = Transaction.objects.get(transaction_ref="txn_test123")
        self.assertEqual(transaction.status, "successful")

    def test_webhook_endpoint_invalid_payload(self):
        """Test webhook with invalid payload"""
        payload = {"invalid": "payload"}

        response = self.client.post(
            self.webhook_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_webhook_endpoint_missing_transaction(self):
        """Test webhook for non-existent transaction"""
        payload = {
            "eventType": "wallet.load.successful",
            "transactionRef": "non-existent",
            "status": "successful",
        }

        response = self.client.post(
            self.webhook_url, data=json.dumps(payload), content_type="application/json"
        )

        # Should return 200 to prevent webhook retries
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class EversendCollectionsTestCase(APITestCase):
    """Test cases for collections endpoints"""

    def test_collection_fee_endpoint(self):
        """Test collection fee calculation"""
        with patch(
            "eversend_payments.collections.services.get_collection_fees"
        ) as mock_fees:
            mock_fees.return_value = {
                "status": "success",
                "data": {"amount": 1000, "charges": 50, "total": 1050},
            }

            url = "/api/eversend-payments/collections/fees/"
            data = {"method": "momo", "currency": "UGX", "amount": 1000}

            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("data", response.data)


class EversendPayoutsTestCase(APITestCase):
    """Test cases for payout endpoints"""

    def setUp(self):
        # Create a wallet for testing
        self.wallet = Wallet.objects.create(
            uuid="test-user-123", currency="USD", amount=Decimal("1000.00")
        )

    def test_payout_insufficient_balance(self):
        """Test payout with insufficient balance"""
        url = "/api/eversend-payments/payout/process/"
        data = {
            "token": "test-token",
            "uuid": "test-user-123",
            "phoneNumber": "+1234567890",
            "firstName": "John",
            "lastName": "Doe",
            "country": "US",
            "serviceFee": 10.00,
            "totalAmount": 2000.00,  # More than available balance
        }

        with patch("eversend_payments.payouts.services.eversend_payout") as mock_payout:
            mock_payout.return_value = {
                "status": "success",
                "data": {
                    "transaction": {"amount": 2000.00, "currency": "USD", "fees": 50.00}
                },
            }

            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("Insufficient balance", response.data["message"])
