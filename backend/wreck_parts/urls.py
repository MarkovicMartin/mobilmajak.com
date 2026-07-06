from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'parts', views.WreckPartViewSet, basename='wreck-parts')

urlpatterns = [
    path('', include(router.urls)),
    path('store-summary/', views.store_summary, name='wreck-parts-store-summary'),
]
