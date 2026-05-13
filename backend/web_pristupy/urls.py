"""
URL routing pro modul web_pristupy
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WebPristupyProdejnyViewSet

# Router pro REST API
router = DefaultRouter()
router.register(r'pristupy', WebPristupyProdejnyViewSet, basename='webpristupy')

app_name = 'web_pristupy'

urlpatterns = [
    # API endpointy
    path('api/', include(router.urls)),
]

# Dokumentace API endpointů:
# GET    /api/pristupy/                    - seznam všech přístupů
# POST   /api/pristupy/                    - vytvoření nového přístupu
# GET    /api/pristupy/{id}/               - detail konkrétního přístupu
# PUT    /api/pristupy/{id}/               - úprava přístupu (admin + prodejce)
# DELETE /api/pristupy/{id}/               - smazání přístupu (pouze admin)
# GET    /api/pristupy/stores/             - statistiky prodejen
# GET    /api/pristupy/categories/         - seznam kategorií
# POST   /api/pristupy/{id}/mark_used/     - označit jako použitý
# GET    /api/pristupy/{id}/reveal_password/ - zobrazit heslo
# GET    /api/pristupy/my_recent/          - nedávno použité přístupy 