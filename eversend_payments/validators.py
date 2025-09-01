from django.conf import settings

def verify_webhook(headers: dict, raw_body: bytes) -> bool:
    """
    TODO: Implement if Eversend provides a signature/HMAC header.
    For now, accept all requests (mirrors PHP which didn’t check).
    """
    secret = settings.EVERSEND_WEBHOOK_SECRET
    if not secret:
        return True
    # e.g., compute HMAC and compare to header value
    return True
