"""
Custom middleware for API endpoints.
"""
from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


class CSRFExemptAPIMiddleware(MiddlewareMixin):
    """
    Middleware to exempt API endpoints from CSRF protection.
    Exempts all URLs starting with '/api/' from CSRF checks.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow browsable API to work properly
        if request.method == 'GET' and 'text/html' in request.META.get('HTTP_ACCEPT', ''):
            pass # continuew processing

        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path.startswith('/api/'):
            # For function-based views
            setattr(view_func, 'csrf_exempt', True)
            # For class-based views
            if hasattr(view_func, 'view_class'):
                view_class = view_func.view_class
                method_decorator(csrf_exempt, name='dispatch')(view_class)
        return None
