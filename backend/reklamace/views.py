from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import ReklamaceNotifikace, ReklamacePolozka, ReklamaceStatus
from .serializers import (
    ReklamaceNotifikaceSerializer,
    ReklamacePolozkaSerializer,
    ReklamacePotvrditSerializer,
)


class ReklamacePolozkaViewSet(ModelViewSet):
    queryset = ReklamacePolozka.objects.filter(is_active=True)
    serializer_class = ReklamacePolozkaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ReklamacePolozka.objects.all()
        if self.request.query_params.get('include_inactive') != '1':
            qs = qs.filter(is_active=True)

        if self.request.query_params.get('include_resolved') != '1':
            qs = qs.exclude(status=ReklamaceStatus.VRIZENE)

        prodejna = self.request.query_params.get('prodejna', '').strip()
        search = self.request.query_params.get('search', '').strip()
        dodavatel = self.request.query_params.get('dodavatel', '').strip()
        status_filter = self.request.query_params.get('status', '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        if prodejna:
            qs = qs.filter(prodejna__iexact=prodejna)
        if dodavatel:
            qs = qs.filter(dodavatel__icontains=dodavatel)
        if search:
            qs = qs.filter(
                Q(nase_znacka__icontains=search)
                | Q(nazev_zbozi__icontains=search)
                | Q(dodavatel__icontains=search)
                | Q(faktura__icontains=search)
                | Q(ean__icontains=search)
                | Q(p_kod__icontains=search)
                | Q(cislo_zasilky__icontains=search)
                | Q(poznamka__icontains=search)
            )
        return qs.order_by('-created_at', '-nase_znacka')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])

    @action(detail=True, methods=['post'])
    def odeslat_dodavateli(self, request, pk=None):
        instance = self.get_object()
        if instance.status != ReklamaceStatus.NEZPRACOVANE:
            return Response(
                {'error': 'Odeslat lze jen nezpracovanou reklamaci.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        now = timezone.now()
        instance.status = ReklamaceStatus.ODESLANE
        instance.odeslano_dodavateli_at = now
        if not instance.datum_odeslani:
            instance.datum_odeslani = now.date()
        instance.save(update_fields=[
            'status', 'odeslano_dodavateli_at', 'datum_odeslani', 'updated_at',
        ])
        return Response(ReklamacePolozkaSerializer(instance).data)

    @action(detail=True, methods=['post'])
    def potvrdit_zpracovani(self, request, pk=None):
        instance = self.get_object()
        serializer = ReklamacePotvrditSerializer(
            data=request.data,
            context={'instance': instance},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        instance.status = ReklamaceStatus.VRIZENE
        instance.zpusob_vyrizeni = data['zpusob_vyrizeni']
        instance.datum_vyrizeni = data.get('datum_vyrizeni') or timezone.now().date()
        if 'sklad_vyskladneno' in data:
            instance.sklad_vyskladneno = data['sklad_vyskladneno']
        if 'sklad_naskladneno' in data:
            instance.sklad_naskladneno = data['sklad_naskladneno']
        instance.save(update_fields=[
            'status', 'zpusob_vyrizeni', 'datum_vyrizeni',
            'sklad_vyskladneno', 'sklad_naskladneno', 'updated_at',
        ])
        return Response(ReklamacePolozkaSerializer(instance).data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def reklamace_notifications(request):
    qs = ReklamaceNotifikace.objects.filter(user=request.user).select_related('reklamace')
    read_param = request.GET.get('read')
    if read_param == '1':
        qs = qs.filter(read_at__isnull=False)
    else:
        qs = qs.filter(read_at__isnull=True)
    return Response(ReklamaceNotifikaceSerializer(qs.order_by('-created_at')[:50], many=True).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reklamace_notifications_mark_read(request):
    ids = request.data.get('ids')
    qs = ReklamaceNotifikace.objects.filter(user=request.user, read_at__isnull=True)
    if ids is not None:
        qs = qs.filter(id__in=ids)
    now = timezone.now()
    updated = qs.update(read_at=now)
    return Response({'marked': updated})
