"""
Views pro modul web_pristupy
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone

from .models import WEB_PRISTUPY_PRODEJNY
from .serializers import (
    WebPristupyProdejnySerializer,
    WebPristupyProdejnyListSerializer,
    WebPristupyProdejnyDetailSerializer,
    StoreStatsSerializer,
    AccessPasswordSerializer
)
from users.models import WebUser


def _web_user(user):
    """Auth backend vrací WebUser přímo, ne Django User s relací webuser."""
    return user if isinstance(user, WebUser) else None


class WebPristupyProdejnyViewSet(viewsets.ModelViewSet):
    """ViewSet pro správu přístupů prodejen"""

    queryset = WEB_PRISTUPY_PRODEJNY.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Vrátí odpovídající serializer podle akce"""
        if self.action == 'list':
            return WebPristupyProdejnyListSerializer
        elif self.action == 'retrieve':
            return WebPristupyProdejnyDetailSerializer
        return WebPristupyProdejnySerializer

    def get_queryset(self):
        """Filtruje data podle parametrů"""
        queryset = WEB_PRISTUPY_PRODEJNY.objects.filter(is_active=True)

        store = self.request.query_params.get('store', None)
        if store:
            queryset = queryset.filter(store__icontains=store)

        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__icontains=category)

        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(company_name__icontains=search) |
                Q(description__icontains=search) |
                Q(notes__icontains=search) |
                Q(website_url__icontains=search)
            )

        return queryset.order_by('store', 'company_name')

    def perform_create(self, serializer):
        """Automatické nastavení added_by při vytváření"""
        serializer.save(added_by=self.request.user.uzivatelske_jmeno)

    def destroy(self, request, *args, **kwargs):
        webuser = _web_user(request.user)
        if not webuser:
            return Response(
                {'error': 'Neplatný uživatel'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if webuser.role != 'ADMIN':
            return Response(
                {'error': 'Pouze administrátor může mazat přístupy'},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def stores(self, request):
        """Vrátí statistiky prodejen"""
        stores_stats = WEB_PRISTUPY_PRODEJNY.get_all_stores()
        serializer = StoreStatsSerializer(stores_stats, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Vrátí seznam všech kategorií"""
        categories = (WEB_PRISTUPY_PRODEJNY.objects
                     .filter(is_active=True, category__isnull=False)
                     .exclude(category='')
                     .values_list('category', flat=True)
                     .distinct()
                     .order_by('category'))
        return Response(list(categories))

    @action(detail=True, methods=['post'])
    def mark_used(self, request, pk=None):
        """Označí přístup jako právě použitý"""
        access = self.get_object()
        access.mark_as_used()
        return Response({
            'message': 'Přístup označen jako použitý',
            'last_used': access.last_used
        })

    @action(detail=True, methods=['get'])
    def reveal_password(self, request, pk=None):
        """Bezpečně odhalí heslo - pouze pro přihlášené uživatele"""
        access = self.get_object()

        access.mark_as_used()

        serializer = AccessPasswordSerializer(data={'access_id': access.id})
        if serializer.is_valid():
            return Response({
                'password': access.password,
                'revealed_at': timezone.now()
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def my_recent(self, request):
        """Vrátí nedávno použité přístupy aktuálního uživatele"""
        recent_accesses = (WEB_PRISTUPY_PRODEJNY.objects
                          .filter(is_active=True, last_used__isnull=False)
                          .order_by('-last_used')[:10])

        serializer = WebPristupyProdejnyListSerializer(recent_accesses, many=True)
        return Response(serializer.data)
