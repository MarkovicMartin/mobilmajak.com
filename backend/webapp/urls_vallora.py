from django.http import JsonResponse
from django.urls import path
from django.utils import timezone

from vallora.views import availability_view, quote_view, search_view


def health_check(_request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "vallora-api",
            "timestamp": timezone.now().isoformat(),
        }
    )


urlpatterns = [
    path("search", search_view, name="vallora-search"),
    path("quote", quote_view, name="vallora-quote"),
    path("availability", availability_view, name="vallora-availability"),
    path("health/", health_check, name="vallora-health"),
]
