from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'polozky', views.ReklamacePolozkaViewSet, basename='reklamace-polozky')

urlpatterns = [
    path('notifikace/', views.reklamace_notifications, name='reklamace-notifikace'),
    path('notifikace/mark-read/', views.reklamace_notifications_mark_read, name='reklamace-notifikace-mark-read'),
    path('', include(router.urls)),
]
