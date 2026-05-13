from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta
from django.db import transaction

from .models import Order, OrderStatusHistory
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderUpdateStatusSerializer,
    OrderStatusHistorySerializer
)


class OrderViewSet(ModelViewSet):
    """ViewSet pro správu objednávek"""
    queryset = Order.objects.all().select_related('zalozil', 'posledni_zmena_uzivatel').prefetch_related('historie_stavu__uzivatel')
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        elif self.action == 'update_status':
            return OrderUpdateStatusSerializer
        return OrderSerializer
    
    def list(self, request):
        """Seznam všech objednávek organizovaný pro kanban board"""
        queryset = self.get_queryset()
        
        # Filtrování podle parametrů
        search = request.query_params.get('search', '')
        status_filter = request.query_params.get('status', '')
        date_from = request.query_params.get('date_from', '')
        date_to = request.query_params.get('date_to', '')
        
        if search:
            queryset = queryset.filter(
                Q(jmeno_zakaznika__icontains=search) |
                Q(prijmeni_zakaznika__icontains=search) |
                Q(telefon_zakaznika__icontains=search) |
                Q(typ_telefonu__icontains=search) |
                Q(dil__icontains=search)
            )
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if date_from:
            queryset = queryset.filter(datum_vytvoreni__date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(datum_vytvoreni__date__lte=date_to)
        
        # Organizace podle stavů pro kanban board
        kanban_data = {}
        for choice in Order.STATUS_CHOICES:
            status_key = choice[0]
            status_label = choice[1]
            
            status_orders = queryset.filter(status=status_key).order_by('-datum_vytvoreni')
            serialized_orders = OrderSerializer(status_orders, many=True).data
            
            kanban_data[status_key] = {
                'label': status_label,
                'orders': serialized_orders,
                'count': len(serialized_orders)
            }
        
        return Response({
            'kanban_data': kanban_data,
            'total_count': queryset.count(),
            'filters': {
                'search': search,
                'status': status_filter,
                'date_from': date_from,
                'date_to': date_to
            }
        })
    
    def create(self, request):
        """Vytvoření nové objednávky"""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save()
            # Vrátíme plný objekt s relacemi
            full_serializer = OrderSerializer(order)
            return Response(full_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, pk=None):
        """Aktualizace objednávky (kromě stavu - k tomu je speciální endpoint)"""
        try:
            order = self.get_object()
            serializer = OrderCreateSerializer(order, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                # Vrátíme plný objekt
                full_serializer = OrderSerializer(order)
                return Response(full_serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            return Response({'error': 'Objednávka nenalezena'}, status=status.HTTP_404_NOT_FOUND)
    
    def destroy(self, request, pk=None):
        """Smazání objednávky"""
        try:
            order = self.get_object()
            order.delete()
            return Response({'message': 'Objednávka byla smazána'}, status=status.HTTP_204_NO_CONTENT)
        except Order.DoesNotExist:
            return Response({'error': 'Objednávka nenalezena'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Speciální endpoint pro změnu stavu objednávky (pro drag & drop)"""
        try:
            order = self.get_object()
            serializer = OrderUpdateStatusSerializer(
                order, 
                data=request.data, 
                context={'request': request}
            )
            if serializer.is_valid():
                updated_order = serializer.save()
                # Vrátíme plný objekt s historií
                full_serializer = OrderSerializer(updated_order)
                return Response(full_serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            return Response({'error': 'Objednávka nenalezena'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Historie změn stavů konkrétní objednávky"""
        try:
            order = self.get_object()
            history = order.historie_stavu.all()
            serializer = OrderStatusHistorySerializer(history, many=True)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response({'error': 'Objednávka nenalezena'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """Statistiky pro dashboard - přehled počtů podle stavů"""
    stats = {}
    
    for choice in Order.STATUS_CHOICES:
        status_key = choice[0]
        status_label = choice[1]
        count = Order.objects.filter(status=status_key).count()
        stats[status_key] = {
            'label': status_label,
            'count': count
        }
    
    # Celkové statistiky
    total_orders = Order.objects.count()
    today_orders = Order.objects.filter(datum_vytvoreni__date=timezone.now().date()).count()
    week_orders = Order.objects.filter(
        datum_vytvoreni__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    return Response({
        'status_stats': stats,
        'total_orders': total_orders,
        'today_orders': today_orders,
        'week_orders': week_orders
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def analytics_data(request):
    """Analytická data pro administrátory - doba trvání procesů"""
    # Pouze pro administrátory
    if request.user.role != 'ADMIN':
        return Response({'error': 'Přístup pouze pro administrátory'}, status=status.HTTP_403_FORBIDDEN)
    
    # Dokončené objednávky za posledních 30 dní
    completed_orders = Order.objects.filter(
        status__in=['hotovo', 'storno'],
        datum_vytvoreni__gte=timezone.now() - timedelta(days=30)
    )
    
    # Výpočet průměrných dob
    process_times = []
    status_times = {}
    
    for order in completed_orders:
        history = list(order.historie_stavu.all().order_by('datum_zmeny'))
        
        if len(history) > 1:
            total_time = history[-1].datum_zmeny - order.datum_vytvoreni
            process_times.append(total_time.total_seconds() / 3600)  # v hodinách
            
            # Časy jednotlivých stavů
            for i, hist in enumerate(history):
                if i == 0:
                    continue  # První záznam přeskakujeme
                
                status_key = hist.novy_status
                doba = hist.doba_ve_stavu
                
                if doba:
                    if status_key not in status_times:
                        status_times[status_key] = []
                    status_times[status_key].append(doba.total_seconds() / 3600)
    
    # Průměrné časy
    avg_total_time = sum(process_times) / len(process_times) if process_times else 0
    avg_status_times = {}
    
    for status_key, times in status_times.items():
        avg_status_times[status_key] = {
            'avg_hours': sum(times) / len(times) if times else 0,
            'count': len(times)
        }
    
    # Nejpomalejší objednávky
    slowest_orders = []
    for order in completed_orders:
        if order.celkova_doba_procesu:
            slowest_orders.append({
                'id': order.id,
                'customer': f"{order.jmeno_zakaznika} {order.prijmeni_zakaznika}",
                'item': f"{order.typ_telefonu} - {order.dil}",
                'total_time_hours': order.celkova_doba_procesu.total_seconds() / 3600,
                'created': order.datum_vytvoreni,
                'completed': order.datum_aktualizace
            })
    
    slowest_orders.sort(key=lambda x: x['total_time_hours'], reverse=True)
    
    return Response({
        'avg_total_time_hours': round(avg_total_time, 2),
        'avg_status_times': avg_status_times,
        'slowest_orders': slowest_orders[:10],  # Top 10 nejpomalejších
        'total_analyzed': len(process_times),
        'analysis_period_days': 30
    }) 