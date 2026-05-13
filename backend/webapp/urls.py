"""
URL configuration for webapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from django.db import connection
from django.utils import timezone
import sys

@ensure_csrf_cookie
def csrf_view(request):
    return JsonResponse({'detail': 'CSRF cookie set'})

def health_check(request):
    """Health check endpoint pro monitoring stavu aplikace"""
    try:
        # Test databázového spojení
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Informace o aplikaci
    response_data = {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "timestamp": timezone.now().isoformat(),
        "database": db_status,
        "python_version": sys.version,
        "django_version": settings.DEBUG,  # Nevystavujeme Django verzi v produkci
        "services": {
            "users": "healthy",
            "news": "healthy", 
            "analytics": "healthy",
            "web_pristupy": "healthy",
            "orders": "healthy"
        }
    }
    
    status_code = 200 if db_status == "healthy" else 503
    return JsonResponse(response_data, status=status_code)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health'),
    path('api/csrf/', csrf_view, name='csrf'),
    path('api/users/', include('users.urls')),
    path('api/news/', include('news.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/shifts/', include('shifts.urls')),
    path('api/stores/', include('stores.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/tasks/', include('tasks.urls')),
    path('api/plans/', include('plans.urls')),
    path('api/tickets/', include('tickets.urls')),
    path('', include('web_pristupy.urls')),
]

# Přidání URL pro media soubory v development módu
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
