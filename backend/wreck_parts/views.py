from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.db.models import Count, Q

from .models import WreckPart
from .serializers import WreckPartSerializer


class WreckPartViewSet(ModelViewSet):
    queryset = WreckPart.objects.filter(is_active=True)
    serializer_class = WreckPartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = WreckPart.objects.all()
        if self.request.query_params.get('include_inactive') != '1':
            qs = qs.filter(is_active=True)

        store = self.request.query_params.get('store', '').strip()
        search = self.request.query_params.get('search', '').strip()
        part_type = self.request.query_params.get('part_type', '').strip()

        if store:
            qs = qs.filter(store__iexact=store)
        if part_type:
            qs = qs.filter(part_type__icontains=part_type)
        if search:
            qs = qs.filter(
                Q(model_name__icontains=search)
                | Q(part_type__icontains=search)
                | Q(notes__icontains=search)
                | Q(store__icontains=search)
            )
        return qs.order_by('store', 'model_name', 'part_type')

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def store_summary(request):
    rows = (
        WreckPart.objects.filter(is_active=True)
        .values('store')
        .annotate(count=Count('id'))
        .order_by('store')
    )
    return Response({'stores': list(rows), 'total': WreckPart.objects.filter(is_active=True).count()})
