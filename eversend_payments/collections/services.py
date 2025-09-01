# payments/collections/services.py
import logging
from typing import Dict, Any
from django.conf import settings
from eversend_payments.services.eversend import make_eversend_request, EversendAPIError

logger = logging.getLogger("payments")

EVERSEND_BASE_URL = "https://api.eversend.co/v1/collections"


def get_collection_fees(method: str, currency: str, amount: float) -> Dict[str, Any]:
    """
    Get collection fees from Eversend API with enhanced error handling
    """
    if not all([method, currency, amount]):
        raise ValueError("Missing required parameters: method, currency, and amount are required")
    
    if amount <= 0:
        raise ValueError("Amount must be greater than 0")
    
    url = f"{EVERSEND_BASE_URL}/fees"
    payload = {
        "method": method.strip(),
        "currency": currency.upper().strip(),
        "amount": float(amount)
    }
    
    try:
        logger.info(f"Requesting collection fees: {payload}")
        response_data = make_eversend_request("POST", url, payload, timeout=15)
        logger.info(f"Collection fees response received for {method}-{currency}-{amount}")
        return response_data
        
    except EversendAPIError as e:
        logger.error(f"Eversend API error getting collection fees: {e}")
        raise ValueError(f"Failed to fetch collection fees: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error getting collection fees: {e}")
        raise ValueError(f"Unexpected error: {str(e)}")


def request_otp(phone: str) -> Dict[str, Any]:
    """
    Request OTP from Eversend API with validation
    """
    if not phone or not phone.strip():
        raise ValueError("Phone number is required")
    
    # Basic phone number validation
    cleaned_phone = phone.strip().replace(" ", "").replace("-", "")
    if len(cleaned_phone) < 10 or not cleaned_phone.replace("+", "").isdigit():
        raise ValueError("Invalid phone number format")
    
    url = f"{EVERSEND_BASE_URL}/otp"
    payload = {"phone": cleaned_phone}
    
    try:
        logger.info(f"Requesting OTP for phone: {cleaned_phone[:5]}***")
        response_data = make_eversend_request("POST", url, payload, timeout=15)
        logger.info(f"OTP request successful for phone: {cleaned_phone[:5]}***")
        return response_data
        
    except EversendAPIError as e:
        logger.error(f"Eversend API error requesting OTP: {e}")
        raise ValueError(f"Failed to request OTP: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error requesting OTP: {e}")
        raise ValueError(f"Unexpected error: {str(e)}")


def initiate_momo_transaction(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initiate mobile money transaction with comprehensive validation
    """
    required_fields = ["phone", "amount", "country", "currency", "transactionRef", "otp", "customer"]
    
    for field in required_fields:
        if not payload.get(field):
            raise ValueError(f"Missing required field: {field}")
    
    # Validate amount
    try:
        amount = float(payload["amount"])
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
    except (ValueError, TypeError):
        raise ValueError("Invalid amount format")
    
    # Validate currency
    currency = payload["currency"].upper().strip()
    if len(currency) != 3:
        raise ValueError("Currency must be a 3-letter code")
    
    # Clean and validate phone
    phone = payload["phone"].strip().replace(" ", "").replace("-", "")
    if len(phone) < 10:
        raise ValueError("Invalid phone number")
    
    url = f"{EVERSEND_BASE_URL}/momo"
    
    # Prepare clean payload
    clean_payload = {
        "phone": phone,
        "amount": amount,
        "country": payload["country"].upper().strip(),
        "currency": currency,
        "transactionRef": payload["transactionRef"].strip(),
        "otp": payload["otp"].strip(),
        "customer": payload["customer"].strip(),
    }
    
    try:
        logger.info(f"Initiating MoMo transaction: {payload['transactionRef']}")
        response_data = make_eversend_request("POST", url, clean_payload, timeout=30)
        logger.info(f"MoMo transaction initiated successfully: {payload['transactionRef']}")
        return response_data
        
    except EversendAPIError as e:
        logger.error(f"Eversend API error initiating MoMo transaction: {e}")
        raise ValueError(f"MoMo transaction failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error initiating MoMo transaction: {e}")
        raise ValueError(f"Unexpected error: {str(e)}")
