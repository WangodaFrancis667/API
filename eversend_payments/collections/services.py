# payments/collections/services.py
import requests
from django.conf import settings
from eversend_payments.services.eversend import get_eversend_token

EVERSEND_BASE_URL = "https://api.eversend.co/v1/collections"


def get_collection_fees(method: str, currency: str, amount: float):
    token = get_eversend_token()
    url = f"{EVERSEND_BASE_URL}/fees"

    payload = {"method": method, "currency": currency, "amount": amount}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers, timeout=15)
    if response.status_code != 200:
        raise ValueError(f"Failed to fetch fees: {response.text}")

    return response.json()


def request_otp(phone: str):
    token = get_eversend_token()
    url = f"{EVERSEND_BASE_URL}/otp"

    payload = {"phone": phone}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers, timeout=15)
    if response.status_code != 200:
        raise ValueError(f"Failed to request OTP: {response.text}")

    return response.json()


def initiate_momo_transaction(payload: dict):
    token = get_eversend_token()
    url = f"{EVERSEND_BASE_URL}/momo"

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers, timeout=20)

    if response.status_code != 200:
        raise ValueError(f"MoMo transaction failed: {response.text}")

    return response.json()
