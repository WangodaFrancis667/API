from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom authentication class that extends JWTAuthentication to support JWT retrieval from cookies.

    This class attempts to authenticate a user by first checking for a JWT in the standard HTTP Authorization header.
    If the header is not present, it then tries to retrieve the JWT from a cookie named "access_token".
    If a valid token is found in the cookie, it validates the token and returns the associated user and token.
    If neither the header nor the cookie contains a valid token, authentication fails and None is returned.

    Methods:
        authenticate(request):
            Attempts to authenticate the request using either the Authorization header or the "access_token" cookie.
            Returns a tuple of (user, validated_token) if authentication is successful, otherwise returns None.
    """
    def authenticate(self, request):
        # Try to get the token from the standard header first
        header = self.get_header(request)
        if header is None:
            # If no header, attempt to retrieve it from the cookie
            raw_token = request.COOKIES.get("access_token")
            if raw_token is None:
                return None
            try:
                validated_token = self.get_validated_token(raw_token)
            except Exception:
                return None
            return self.get_user(validated_token), validated_token
        return super().authenticate(request)