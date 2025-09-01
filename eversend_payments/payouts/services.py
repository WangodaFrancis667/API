import logging
from typing import Dict, Any
from django.conf import settings
from eversend_payments.services.eversend import make_eversend_request, EversendAPIError

logger = logging.getLogger("payments")

EVERSEND_BASE_URL = "https://api.eversend.co/v1"


def eversend_payout(
    token: str, 
    country: str, 
    phone: str, 
    first_name: str, 
    last_name: str, 
    transaction_ref: str
) -> Dict[str, Any]:
    """
    Process payout through Eversend API with validation
    """
    # Validate required fields
    required_fields = {
        "token": token,
        "country": country,
        "phone": phone,
        "first_name": first_name,
        "last_name": last_name,
        "transaction_ref": transaction_ref,
    }
    
    for field_name, field_value in required_fields.items():
        if not field_value or not str(field_value).strip():
            raise ValueError(f"Missing or empty required field: {field_name}")
    
    # Clean and validate phone number
    cleaned_phone = phone.strip().replace(" ", "").replace("-", "")
    if len(cleaned_phone) < 10:
        raise ValueError("Invalid phone number format")
    
    # Validate names (basic validation)
    if len(first_name.strip()) < 2 or len(last_name.strip()) < 2:
        raise ValueError("First name and last name must be at least 2 characters")
    
    url = f"{EVERSEND_BASE_URL}/payouts"
    
    payload = {
        "token": token.strip(),
        "country": country.upper().strip(),
        "phoneNumber": cleaned_phone,
        "firstName": first_name.strip().title(),
        "lastName": last_name.strip().title(),
        "transactionRef": transaction_ref.strip(),
    }
    
    try:
        logger.info(f"Processing payout: {transaction_ref}")
        response_data = make_eversend_request("POST", url, payload, timeout=45)
        logger.info(f"Payout processed successfully: {transaction_ref}")
        return response_data
        
    except EversendAPIError as e:
        logger.error(f"Eversend API error processing payout: {e}")
        raise ValueError(f"Payout failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error processing payout: {e}")
        raise ValueError(f"Unexpected error: {str(e)}")


def eversend_payout_quotation(
    source_wallet: str, 
    amount: float, 
    payout_type: str, 
    destination_country: str, 
    destination_currency: str, 
    amount_type: str
) -> Dict[str, Any]:
    """
    Get payout quotation from Eversend API with validation
    """
    # Validate required fields
    required_fields = {
        "source_wallet": source_wallet,
        "amount": amount,
        "payout_type": payout_type,
        "destination_country": destination_country,
        "destination_currency": destination_currency,
        "amount_type": amount_type,
    }
    
    for field_name, field_value in required_fields.items():
        if field_value is None or (isinstance(field_value, str) and not field_value.strip()):
            raise ValueError(f"Missing or empty required field: {field_name}")
    
    # Validate amount
    try:
        amount_value = float(amount)
        if amount_value <= 0:
            raise ValueError("Amount must be greater than 0")
    except (ValueError, TypeError):
        raise ValueError("Invalid amount format")
    
    # Validate currencies (basic validation)
    if len(source_wallet.strip()) != 3:
        raise ValueError("Source wallet must be a 3-letter currency code")
    
    if len(destination_currency.strip()) != 3:
        raise ValueError("Destination currency must be a 3-letter currency code")
    
    url = f"{EVERSEND_BASE_URL}/payouts/quotation"
    
    payload = {
        "sourceWallet": source_wallet.upper().strip(),
        "amount": amount_value,
        "type": payout_type.strip().lower(),
        "destinationCountry": destination_country.upper().strip(),
        "destinationCurrency": destination_currency.upper().strip(),
        "amountType": amount_type.strip().lower(),
    }
    
    try:
        logger.info(f"Requesting payout quotation: {source_wallet} -> {destination_currency}, Amount: {amount_value}")
        response_data = make_eversend_request("POST", url, payload, timeout=30)
        logger.info(f"Payout quotation received successfully")
        return response_data
        
    except EversendAPIError as e:
        logger.error(f"Eversend API error getting payout quotation: {e}")
        raise ValueError(f"Failed to get payout quotation: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error getting payout quotation: {e}")
        raise ValueError(f"Unexpected error: {str(e)}")
