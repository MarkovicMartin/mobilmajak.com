"""
Views pro modul web_pristupy
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.utils import timezone

from .models import WEB_PRISTUPY_PRODEJNY
from .permissions import (
    exclude_admin_category_q,
    is_admin_category,
    is_admin_user,
    is_web_user,
)
from .serializers import (
    WebPristupyProdejnySerializer,
    WebPristupyProdejnyListSerializer,
    WebPristupyProdejnyDetailSerializer,
    StoreStatsSerializer,
    AccessPasswordSerializer
)


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
        """Filtruje data podle parametrů; Admin kategorie jen pro ADMIN."""
        queryset = WEB_PRISTUPY_PRODEJNY.objects.filter(is_active=True)
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(exclude_admin_category_q())

        store = self.request.query_params.get('store', None)
        if store:
            queryset = queryset.filter(store__icontains=store)

        category = self.request.query_params.get('category', None)
        if category:
            if is_admin_category(category) and not is_admin_user(self.request.user):
                return queryset.none()
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

    def create(self, request, *args, **kwargs):
        if is_admin_category(request.data.get('category')) and not is_admin_user(request.user):
            return Response(
                {'error': 'Kategorii Admin mohou spravovat jen administrátoři'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not is_admin_user(request.user):
            if is_admin_category(instance.category) or is_admin_category(request.data.get('category')):
                return Response(
                    {'error': 'Kategorii Admin mohou spravovat jen administrátoři'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not is_admin_user(request.user):
            if is_admin_category(instance.category) or is_admin_category(request.data.get('category')):
                return Response(
                    {'error': 'Kategorii Admin mohou spravovat jen administrátoři'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Automatické nastavení added_by při vytváření"""
        serializer.save(added_by=self.request.user.uzivatelske_jmeno)

    def destroy(self, request, *args, **kwargs):
        webuser = is_web_user(request.user)
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
        """Vrátí statistiky prodejen (bez Admin záznamů pro ne-adminy)."""
        qs = WEB_PRISTUPY_PRODEJNY.objects.filter(is_active=True)
        if not is_admin_user(request.user):
            qs = qs.filter(exclude_admin_category_q())
        stores_stats = (
            qs.values('store')
            .annotate(count=Count('id'))
            .order_by('store')
        )
        serializer = StoreStatsSerializer(stores_stats, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Vrátí seznam kategorií; Admin jen pro ADMIN."""
        categories = (WEB_PRISTUPY_PRODEJNY.objects
                     .filter(is_active=True, category__isnull=False)
                     .exclude(category='')
                     .values_list('category', flat=True)
                     .distinct()
                     .order_by('category'))
        if not is_admin_user(request.user):
            categories = [
                c for c in categories
                if not is_admin_category(c)
            ]
            return Response(list(categories))
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
        """Odhalí heslo; Admin kategorie jen pro ADMIN."""
        access = self.get_object()
        if is_admin_category(access.category) and not is_admin_user(request.user):
            return Response(
                {'error': 'Hesla kategorie Admin jsou dostupná jen administrátorům'},
                status=status.HTTP_403_FORBIDDEN,
            )

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
        recent_accesses = self.get_queryset().filter(
            last_used__isnull=False
        ).order_by('-last_used')[:10]

        serializer = WebPristupyProdejnyListSerializer(recent_accesses, many=True)
        return Response(serializer.data)
