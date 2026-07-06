from rest_framework import permissions
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import DailyDutyTemplate
from .serializers import DailyDutyTemplateSerializer


class DailyDutyTemplateViewSet(ReadOnlyModelViewSet):
    queryset = DailyDutyTemplate.objects.filter(is_active=True)
    serializer_class = DailyDutyTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
