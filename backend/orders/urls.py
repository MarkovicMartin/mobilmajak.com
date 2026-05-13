from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Vytvoříme router pro ViewSet
router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='orders')

urlpatterns = [
    # ViewSet endpoints (automaticky generované)
    path('', include(router.urls)),
    
    # Další užitečné endpointy
    path('dashboard-stats/', views.dashboard_stats, name='dashboard-stats'),
    path('analytics/', views.analytics_data, name='analytics-data'),
]

# Výsledné endpointy:
# GET    /api/orders/                     - Kanban board data (seznam podle stavů)
# POST   /api/orders/                     - Vytvoření nové objednávky
# GET    /api/orders/{id}/                - Detail objednávky
# PUT    /api/orders/{id}/                - Úplná aktualizace objednávky
# PATCH  /api/orders/{id}/                - Částečná aktualizace objednávky
# DELETE /api/orders/{id}/                - Smazání objednávky
# PATCH  /api/orders/{id}/update_status/  - Změna stavu objednávky (pro drag & drop)
# GET    /api/orders/{id}/history/        - Historie změn stavů
# GET    /api/orders/dashboard-stats/     - Statistiky pro dashboard
# GET    /api/orders/analytics/           - Analytická data (pouze admin) 