import logging
import requests
from django.conf import settings

logger = logging.getLogger("payments")

EVERSEND_TOKEN_URL = "https://api.eversend.co/v1/auth/token"

def get_eversend_token() -> str | None:
    """
    Replacement for PHP getEversendToken().
    Returns the access token string or None.
    """
    headers = {
        "clientId": settings.EVERSEND_CLIENT_ID,
        "clientSecret": settings.EVERSEND_CLIENT_SECRET,
    }
    try:
        resp = requests.get(EVERSEND_TOKEN_URL, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        token = data.get("token")
        if not token:
            logger.error("Eversend token response missing 'token': %s", data)
        return token
    except requests.RequestException as e:
        logger.exception("Failed to retrieve Eversend token: %s", e)
        return None
