import logging
import time
from typing import Optional
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("payments")

EVERSEND_TOKEN_URL = "https://api.eversend.co/v1/auth/token"
TOKEN_CACHE_KEY = "eversend_access_token"
TOKEN_CACHE_TIMEOUT = 3600  # 1 hour


class EversendAPIError(Exception):
    """Custom exception for Eversend API errors"""

    def __init__(
        self, message: str, status_code: int = None, response_data: dict = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


def get_eversend_token(force_refresh: bool = False) -> Optional[str]:
    """
    Get Eversend access token with caching and error handling.
    Returns the access token string or None if failed.
    """
    # Check cache first unless force refresh
    if not force_refresh:
        cached_token = cache.get(TOKEN_CACHE_KEY)
        if cached_token:
            logger.debug("Retrieved Eversend token from cache")
            return cached_token

    client_id = getattr(settings, "EVERSEND_CLIENT_ID", "")
    client_secret = getattr(settings, "EVERSEND_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        logger.error("EVERSEND_CLIENT_ID or EVERSEND_CLIENT_SECRET not configured")
        return None

    headers = {
        "clientId": client_id,
        "clientSecret": client_secret,
        "Content-Type": "application/json",
        "User-Agent": "Django-EversendPayments/1.0",
    }

    try:
        logger.info("Requesting new Eversend access token")

        resp = requests.get(
            EVERSEND_TOKEN_URL,
            headers=headers,
            timeout=30,
            verify=True,  # Ensure SSL verification
        )

        # Log response status for debugging
        logger.info(f"Eversend token request: {resp.status_code}")

        resp.raise_for_status()
        data = resp.json()

        token = data.get("token")
        if not token:
            logger.error(f"Eversend token response missing 'token' field: {data}")
            return None

        # Cache the token
        cache.set(TOKEN_CACHE_KEY, token, TOKEN_CACHE_TIMEOUT)
        logger.info("Successfully retrieved and cached Eversend token")

        return token

    except requests.exceptions.Timeout:
        logger.error("Timeout while requesting Eversend token")
        return None
    except requests.exceptions.ConnectionError:
        logger.error("Connection error while requesting Eversend token")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error while requesting Eversend token: {e}")
        if e.response is not None:
            logger.error(f"Response content: {e.response.text}")
        return None
    except requests.RequestException as e:
        logger.exception(f"Unexpected error while requesting Eversend token: {e}")
        return None
    except (KeyError, ValueError, TypeError) as e:
        logger.exception(f"Error parsing Eversend token response: {e}")
        return None


def make_eversend_request(
    method: str, url: str, data: dict = None, timeout: int = 30, retry_count: int = 1
) -> dict:
    """
    Make authenticated request to Eversend API with retry logic
    """
    for attempt in range(retry_count + 1):
        token = get_eversend_token(force_refresh=attempt > 0)
        if not token:
            raise EversendAPIError("Failed to obtain access token")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Django-EversendPayments/1.0",
        }

        try:
            if method.upper() == "GET":
                resp = requests.get(
                    url, headers=headers, params=data, timeout=timeout, verify=True
                )
            elif method.upper() == "POST":
                resp = requests.post(
                    url, headers=headers, json=data, timeout=timeout, verify=True
                )
            else:
                raise EversendAPIError(f"Unsupported HTTP method: {method}")

            # If we get 401, token might be expired, try refresh on next attempt
            if resp.status_code == 401 and attempt < retry_count:
                logger.warning(
                    f"Got 401 from Eversend API, attempting token refresh (attempt {attempt + 1})"
                )
                cache.delete(TOKEN_CACHE_KEY)  # Clear cached token
                time.sleep(1)  # Brief delay before retry
                continue

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.Timeout:
            if attempt == retry_count:
                raise EversendAPIError(
                    f"Request timeout after {retry_count + 1} attempts"
                )
            time.sleep(2**attempt)  # Exponential backoff

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            raise EversendAPIError(
                error_msg,
                e.response.status_code,
                e.response.json() if e.response else None,
            )

        except requests.RequestException as e:
            if attempt == retry_count:
                raise EversendAPIError(
                    f"Request failed after {retry_count + 1} attempts: {str(e)}"
                )
            time.sleep(2**attempt)

    raise EversendAPIError("Max retry attempts exceeded")
