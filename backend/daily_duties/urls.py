from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'templates', views.DailyDutyTemplateViewSet, basename='daily-duties')

urlpatterns = [
    path('mine/', views.MyDutiesView.as_view(), name='daily-duties-mine'),
    path('mine/<int:pk>/complete/', views.CompleteDutyView.as_view(), name='daily-duties-complete'),
    path('status/', views.DutyStatusView.as_view(), name='daily-duties-status'),
    path('', include(router.urls)),
]
