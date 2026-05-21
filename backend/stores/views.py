from django.shortcuts import render
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Prodejna
from .serializers import ProdejnaSerializer, ProdejnaListSerializer, ProdejnaChoiceSerializer
from .vedouci_sync import assign_vedouci_prodejny

class ProdejnaViewSet(viewsets.ModelViewSet):
    """ViewSet pro správu prodejen"""
    
    queryset = Prodejna.objects.all()
    serializer_class = ProdejnaSerializer
    
    def get_serializer_class(self):
        """Vybere správný serializer podle akce"""
        if self.action == 'list':
            return ProdejnaListSerializer
        elif self.action == 'choices':
            return ProdejnaChoiceSerializer
        return ProdejnaSerializer
    
    def get_queryset(self):
        """Filtruje prodejny podle parametrů"""
        queryset = Prodejna.objects.all()
        
        # Filtr podle aktivního stavu
        aktivni = self.request.query_params.get('aktivni', None)
        if aktivni is not None:
            if aktivni.lower() in ['true', '1']:
                queryset = queryset.filter(aktivni=True)
            elif aktivni.lower() in ['false', '0']:
                queryset = queryset.filter(aktivni=False)
        
        # Vyhledávání podle názvu
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(nazev__icontains=search) |
                Q(nazev_kratkiy__icontains=search) |
                Q(nazev_google_sheets__icontains=search)
            )
        
        return queryset.order_by('poradi', 'nazev')
    
    def list(self, request):
        """Seznam všech prodejen"""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                'success': True,
                'stores': serializer.data,
                'count': queryset.count()
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Chyba při načítání prodejen: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, pk=None):
        """Detail jedné prodejny"""
        try:
            prodejna = self.get_object()
            serializer = self.get_serializer(prodejna)
            
            return Response({
                'success': True,
                'store': serializer.data
            })
        except Prodejna.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Prodejna nebyla nalezena'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Chyba při načítání prodejny: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _sync_vedouci_after_save(self, prodejna, request_data, previous_vedouci_id=None):
        if 'vedouci_user_id' not in request_data:
            return prodejna
        new_id = request_data.get('vedouci_user_id')
        if new_id in ('', None) and previous_vedouci_id:
            assign_vedouci_prodejny(prodejna.id, None)
        elif new_id not in ('', None):
            assign_vedouci_prodejny(prodejna.id, new_id)
        return Prodejna.objects.get(pk=prodejna.pk)

    def create(self, request):
        """Vytvoření nové prodejny"""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                prodejna = serializer.save()
                prodejna = self._sync_vedouci_after_save(prodejna, request.data)
                return Response({
                    'success': True,
                    'message': 'Prodejna byla úspěšně vytvořena',
                    'store': ProdejnaSerializer(prodejna).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'message': 'Neplatná data',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Chyba při vytváření prodejny: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, pk=None):
        """Aktualizace prodejny"""
        try:
            prodejna = self.get_object()
            previous_vedouci_id = prodejna.vedouci_user_id
            serializer = self.get_serializer(prodejna, data=request.data, partial=True)
            
            if serializer.is_valid():
                prodejna = serializer.save()
                prodejna = self._sync_vedouci_after_save(
                    prodejna, request.data, previous_vedouci_id=previous_vedouci_id
                )
                return Response({
                    'success': True,
                    'message': 'Prodejna byla úspěšně aktualizována',
                    'store': ProdejnaSerializer(prodejna).data
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Neplatná data',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Prodejna.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Prodejna nebyla nalezena'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Chyba při aktualizaci prodejny: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, pk=None):
        """Smazání prodejny"""
        try:
            prodejna = self.get_object()
            
            # Kontrola, zda není prodejna používána uživateli
            if prodejna.uzivatele.exists():
                return Response({
                    'success': False,
                    'message': f'Prodejnu nelze smazat, protože je přiřazena {prodejna.uzivatele.count()} uživatelům'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Kontrola, zda není prodejna používána směnami
            if prodejna.smeny.exists():
                return Response({
                    'success': False,
                    'message': f'Prodejnu nelze smazat, protože má {prodejna.smeny.count()} směn'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            prodejna_nazev = prodejna.nazev
            prodejna.delete()
            
            return Response({
                'success': True,
                'message': f'Prodejna "{prodejna_nazev}" byla úspěšně smazána'
            })
        except Prodejna.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Prodejna nebyla nalezena'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Chyba při mazání prodejny: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def choices(self, request):
        """Endpoint pro dropdown seznamy - pouze aktivní prodejny"""
        try:
            queryset = Prodejna.get_aktivni_prodejny()
            serializer = ProdejnaChoiceSerializer(queryset, many=True)
            
            return Response({
                'success': True,
                'stores': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Chyba při načítání seznamu prodejen: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def bulk_update_status(self, request):
        """Hromadná změna statusu prodejen"""
        try:
            store_ids = request.data.get('store_ids', [])
            new_status = request.data.get('aktivni', True)
            
            if not store_ids:
                return Response({
                    'success': False,
                    'message': 'Nebyla vybrána žádná prodejna'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            updated_count = Prodejna.objects.filter(id__in=store_ids).update(aktivni=new_status)
            
            return Response({
                'success': True,
                'message': f'Status byl změněn u {updated_count} prodejen',
                'updated_count': updated_count
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Chyba při hromadné aktualizaci: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
