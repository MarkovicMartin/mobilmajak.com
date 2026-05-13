from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProdejnaViewSet

# Router pro REST API endpoints
router = DefaultRouter()
router.register(r'prodejny', ProdejnaViewSet, basename='prodejny')

app_name = 'stores'

urlpatterns = [
    # REST API endpoints
    path('', include(router.urls)),
] 