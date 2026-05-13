from django.middleware.csrf import CsrfViewMiddleware
from django.http import HttpResponseForbidden

class ApiCsrfMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Pro API endpointy ignorujeme CSRF
        if request.path.startswith('/api/'):
            # Přeskočíme CSRF kontrolu pro API
            return self.get_response(request)
        
        # Pro ostatní endpointy použijeme standardní CSRF middleware
        csrf_middleware = CsrfViewMiddleware(self.get_response)
        return csrf_middleware(request) 