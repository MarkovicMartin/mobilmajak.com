from django.shortcuts import render
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Novinka, NovinkaSoubor, Reakce, Komentar, KomentarSoubor, Kategorie
from .serializers import (
    NovinkaSerializer, NovinkaCreateSerializer,
    KomentarSerializer, KomentarCreateSerializer,
    ReakceSerializer, ReakceCreateSerializer,
    NovinkaSouborSerializer, KomentarSouborSerializer,
    KategorieSerializer
)
from users.models import WebUser
from rest_framework.exceptions import ValidationError

class NovinkaListCreateView(generics.ListCreateAPIView):
    """View pro seznam a vytváření novinek"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Novinka.objects.filter(aktivni=True).select_related('autor').prefetch_related(
            'soubory', 'reakce__uzivatel', 'komentare__autor', 'komentare__soubory', 'kategorie'
        )
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return NovinkaCreateSerializer
        return NovinkaSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        print(f"DEBUG: Vytváří se příspěvek s daty: {self.request.data}")
        super().perform_create(serializer)

class NovinkaDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View pro detail, úpravu a smazání novinky"""
    permission_classes = [IsAuthenticated]
    queryset = Novinka.objects.filter(aktivni=True).select_related('autor').prefetch_related(
        'soubory', 'reakce__uzivatel', 'komentare__autor', 'komentare__soubory', 'kategorie'
    )
    serializer_class = NovinkaSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def destroy(self, request, *args, **kwargs):
        novinka = self.get_object()
        # Kontrola oprávnění - pouze autor nebo admin může mazat
        if request.user.role != 'ADMIN' and request.user != novinka.autor:
            return Response(
                {'error': 'Nemáte oprávnění smazat tuto novinku'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Administrátor skutečně maže z databáze, autor jen deaktivuje
        if request.user.role == 'ADMIN':
            novinka.delete()  # Skutečné smazání z databáze
            return Response({'message': 'Novinka byla natrvalo smazána z databáze'}, status=status.HTTP_200_OK)
        else:
            # Autor jen deaktivuje
            novinka.aktivni = False
            novinka.save()
            return Response({'message': 'Novinka byla skryta'}, status=status.HTTP_200_OK)

class KomentarListCreateView(generics.ListCreateAPIView):
    """View pro seznam a vytváření komentářů k novince"""
    permission_classes = [IsAuthenticated]
    serializer_class = KomentarSerializer
    
    def get_queryset(self):
        novinka_id = self.kwargs.get('novinka_id')
        return Komentar.objects.filter(
            novinka_id=novinka_id, 
            aktivni=True
        ).select_related('autor').prefetch_related('soubory')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return KomentarCreateSerializer
        return KomentarSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        """Přiřadí novinku z URL parametru k novému komentáři"""
        novinka_id = self.kwargs.get('novinka_id')
        try:
            novinka = Novinka.objects.get(id=novinka_id, aktivni=True)
            serializer.save(novinka=novinka)
        except Novinka.DoesNotExist:
            raise ValidationError({'error': 'Novinka neexistuje nebo není aktivní'})

class KomentarDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View pro detail, úpravu a smazání komentáře"""
    permission_classes = [IsAuthenticated]
    serializer_class = KomentarSerializer
    
    def get_queryset(self):
        return Komentar.objects.filter(aktivni=True).select_related('autor').prefetch_related('soubory')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def destroy(self, request, *args, **kwargs):
        komentar = self.get_object()
        # Kontrola oprávnění - pouze autor nebo admin může mazat
        if request.user.role != 'ADMIN' and request.user != komentar.autor:
            return Response(
                {'error': 'Nemáte oprávnění smazat tento komentář'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Administrátor skutečně maže z databáze, autor jen deaktivuje
        if request.user.role == 'ADMIN':
            komentar.delete()  # Skutečné smazání z databáze
            return Response({'message': 'Komentář byl natrvalo smazán z databáze'}, status=status.HTTP_200_OK)
        else:
            # Autor jen deaktivuje
            komentar.aktivni = False
            komentar.save()
            return Response({'message': 'Komentář byl skryt'}, status=status.HTTP_200_OK)

class ReakceCreateView(generics.CreateAPIView):
    """View pro vytváření reakcí na novinky"""
    permission_classes = [IsAuthenticated]
    serializer_class = ReakceCreateSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def odstranit_reakci(request, novinka_id):
    """Odstraní reakci uživatele na novinku"""
    try:
        reakce = Reakce.objects.get(novinka_id=novinka_id, uzivatel=request.user)
        reakce.delete()
        return Response({'message': 'Reakce byla odstraněna'}, status=status.HTTP_200_OK)
    except Reakce.DoesNotExist:
        return Response(
            {'error': 'Reakce nebyla nalezena'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nahrat_soubor_novinky(request, novinka_id):
    """Nahraje soubor k novince"""
    try:
        novinka = get_object_or_404(Novinka, id=novinka_id, aktivni=True)
        
        if 'soubor' not in request.FILES:
            return Response(
                {'error': 'Nebyl vybrán žádný soubor'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        soubor = request.FILES['soubor']
        
        # Určení typu souboru podle přípony
        nazev = soubor.name
        pripona = nazev.split('.')[-1].lower()
        
        if pripona in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            typ = 'obrazek'
        elif pripona in ['pdf', 'doc', 'docx', 'txt']:
            typ = 'dokument'
        elif pripona in ['mp4', 'avi', 'mov', 'wmv']:
            typ = 'video'
        elif pripona in ['mp3', 'wav', 'ogg']:
            typ = 'audio'
        else:
            typ = 'jiny'
        
        novinka_soubor = NovinkaSoubor.objects.create(
            novinka=novinka,
            soubor=soubor,
            nazev=nazev,
            typ=typ,
            velikost=soubor.size
        )
        
        serializer = NovinkaSouborSerializer(novinka_soubor, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Chyba při nahrávání souboru: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nahrat_soubor_komentare(request, komentar_id):
    """Nahraje soubor k komentáři"""
    try:
        komentar = get_object_or_404(Komentar, id=komentar_id, aktivni=True)
        
        if 'soubor' not in request.FILES:
            return Response(
                {'error': 'Nebyl vybrán žádný soubor'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        soubor = request.FILES['soubor']
        
        # Určení typu souboru podle přípony
        nazev = soubor.name
        pripona = nazev.split('.')[-1].lower()
        
        if pripona in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            typ = 'obrazek'
        elif pripona in ['pdf', 'doc', 'docx', 'txt']:
            typ = 'dokument'
        elif pripona in ['mp4', 'avi', 'mov', 'wmv']:
            typ = 'video'
        elif pripona in ['mp3', 'wav', 'ogg']:
            typ = 'audio'
        else:
            typ = 'jiny'
        
        komentar_soubor = KomentarSoubor.objects.create(
            komentar=komentar,
            soubor=soubor,
            nazev=nazev,
            typ=typ,
            velikost=soubor.size
        )
        
        serializer = KomentarSouborSerializer(komentar_soubor, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Chyba při nahrávání souboru: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def odstranit_soubor_novinky(request, soubor_id):
    """Odstraní soubor z novinky"""
    try:
        soubor = get_object_or_404(NovinkaSoubor, id=soubor_id)
        novinka = soubor.novinka
        
        # Kontrola oprávnění - pouze autor novinky nebo admin může mazat soubory
        if request.user.role != 'ADMIN' and request.user != novinka.autor:
            return Response(
                {'error': 'Nemáte oprávnění smazat tento soubor'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        soubor.delete()
        return Response({'message': 'Soubor byl smazán'}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Chyba při mazání souboru: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def odstranit_soubor_komentare(request, soubor_id):
    """Odstraní soubor z komentáře"""
    try:
        soubor = get_object_or_404(KomentarSoubor, id=soubor_id)
        komentar = soubor.komentar
        
        # Kontrola oprávnění - pouze autor komentáře nebo admin může mazat soubory
        if request.user.role != 'ADMIN' and request.user != komentar.autor:
            return Response(
                {'error': 'Nemáte oprávnění smazat tento soubor'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        soubor.delete()
        return Response({'message': 'Soubor byl smazán'}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Chyba při mazání souboru: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class KategorieListView(generics.ListAPIView):
    """View pro seznam kategorií (všichni uživatelé)"""
    permission_classes = [IsAuthenticated]
    queryset = Kategorie.objects.filter(aktivni=True)
    serializer_class = KategorieSerializer

class KategorieCreateView(generics.CreateAPIView):
    """View pro vytváření kategorií (pouze admin)"""
    permission_classes = [IsAuthenticated]
    serializer_class = KategorieSerializer
    
    def perform_create(self, serializer):
        # Pouze admin může vytvářet kategorie
        if self.request.user.role != 'ADMIN':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Pouze administrátor může vytvářet kategorie")
        serializer.save()

class KategorieDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View pro detail, úpravu a smazání kategorie (pouze admin)"""
    permission_classes = [IsAuthenticated]
    queryset = Kategorie.objects.all()
    serializer_class = KategorieSerializer
    
    def perform_update(self, serializer):
        # Pouze admin může upravovat kategorie
        if self.request.user.role != 'ADMIN':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Pouze administrátor může upravovat kategorie")
        serializer.save()
    
    def perform_destroy(self, instance):
        # Pouze admin může mazat kategorie
        if self.request.user.role != 'ADMIN':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Pouze administrátor může mazat kategorie")
        instance.delete()
