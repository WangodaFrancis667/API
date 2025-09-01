import requests
from django.conf import settings

EVERSEND_BASE_URL = "https://api.eversend.co/v1"

def get_eversend_token():
    """
    Fetch authentication token for Eversend.
    Should be stored securely or retrieved via OAuth flow.
    """
    # Example placeholder; adapt to your implementation
    return settings.EVERSEND_API_KEY


def eversend_payout(token, country, phone, first_name, last_name, transaction_ref):
    url = f"{EVERSEND_BASE_URL}/payouts"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_eversend_token()}",
    }
    payload = {
        "token": token,
        "country": country,
        "phoneNumber": phone,
        "firstName": first_name,
        "lastName": last_name,
        "transactionRef": transaction_ref,
    }
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    return response


def eversend_payout_quotation(source_wallet, amount, payout_type, destination_country, destination_currency, amount_type):
    url = f"{EVERSEND_BASE_URL}/payouts/quotation"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_eversend_token()}",
    }
    payload = {
        "sourceWallet": source_wallet,
        "amount": amount,
        "type": payout_type,
        "destinationCountry": destination_country,
        "destinationCurrency": destination_currency,
        "amountType": amount_type,
    }
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    return response
