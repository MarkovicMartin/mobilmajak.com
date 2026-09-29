from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import KnowledgeAskView, KnowledgeDocumentViewSet

router = DefaultRouter()
router.register(r'documents', KnowledgeDocumentViewSet, basename='knowledge-document')

urlpatterns = [
    path('ask/', KnowledgeAskView.as_view(), name='knowledge-ask'),
    path('', include(router.urls)),
]
