from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import login, logout
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.middleware.csrf import get_token
import os
import uuid

from .models import WebUser, ProfilovyObrazek
from .serializers import (
    WebUserSerializer, WebUserCreateSerializer, WebUserUpdateSerializer,
    LoginSerializer, WebUserProfileSerializer, WebUserPasswordChangeSerializer,
    ProfilovyObrazekSerializer
)

# Create your views here.

@ensure_csrf_cookie
def csrf_token_view(request):
    """Endpoint pro získání CSRF tokenu"""
    return JsonResponse({
        'csrfToken': get_token(request),
        'success': True
    })

@api_view(['POST'])
@permission_classes([])  # Povolíme přístup bez autentifikace
@csrf_exempt
def login_view(request):
    """Přihlášení uživatele"""
    # Debug log (bez hesla)
    try:
        incoming_username = None
        if isinstance(getattr(request, 'data', None), dict):
            incoming_username = request.data.get('uzivatelske_jmeno') or request.data.get('username')
        print(f"LOGIN: incoming payload username='{incoming_username}' path='{request.path}' content_type='{request.content_type}'")
    except Exception:
        pass

    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        # Přihlášení uživatele
        login(request, user)
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        # Uložení session
        request.session.save()
        
        print(f"LOGIN: Posílám data uživatele {user.id}: {WebUserSerializer(user).data}")
        print(f"Uživatel {user.id} úspěšně přihlášen, session ID: {request.session.session_key}")
        
        user_data = WebUserSerializer(user).data
        return Response({
            'success': True,
            'message': 'Přihlášení úspěšné',
            'user': user_data
        })
    
    # Pokud serializer selže, vrátíme sjednocenou odpověď 401 (špatné údaje)
    print(f"LOGIN: validation failed, errors={serializer.errors}")
    return Response({'success': False, 'message': 'Neplatné přihlašovací údaje', 'errors': serializer.errors}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list(request):
    """Seznam uživatelů (pro ADMIN a VEDOUCI)"""
    # Kontrola, zda je uživatel admin nebo vedoucí
    if not hasattr(request.user, 'role') or request.user.role not in ['ADMIN', 'VEDOUCI']:
        return Response({
            'success': False,
            'message': 'Nemáte oprávnění k zobrazení seznamu uživatelů'
        }, status=status.HTTP_403_FORBIDDEN)
    
    users = WebUser.objects.all()
    serializer = WebUserSerializer(users, many=True)
    
    return Response({
        'success': True,
        'users': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_user(request):
    """Vytvoření nového uživatele (pouze pro adminy)"""
    # Kontrola, zda je uživatel admin
    if not hasattr(request.user, 'role') or request.user.role != 'ADMIN':
        return Response({
            'success': False,
            'message': 'Nemáte oprávnění k vytváření uživatelů'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = WebUserCreateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'message': 'Uživatel byl úspěšně vytvořen',
            'user': serializer.data
        })
    
    return Response({
        'success': False,
        'message': 'Chyba při vytváření uživatele',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user(request, user_id):
    """Aktualizace uživatele (pouze pro adminy)"""
    # Kontrola, zda je uživatel admin
    if not hasattr(request.user, 'role') or request.user.role != 'ADMIN':
        return Response({
            'success': False,
            'message': 'Nemáte oprávnění k úpravě uživatelů'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = WebUser.objects.get(id=user_id)
    except WebUser.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Uživatel nebyl nalezen'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = WebUserCreateSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'message': 'Uživatel byl úspěšně aktualizován',
            'user': serializer.data
        })
    
    return Response({
        'success': False,
        'message': 'Chyba při aktualizaci uživatele',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user(request, user_id):
    """Smazání uživatele (pouze pro adminy)"""
    # Kontrola, zda je uživatel admin
    if not hasattr(request.user, 'role') or request.user.role != 'ADMIN':
        return Response({
            'success': False,
            'message': 'Nemáte oprávnění k mazání uživatelů'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Zabránit smazání sebe sama
    if request.user.id == user_id:
        return Response({
            'success': False,
            'message': 'Nemůžete smazat svůj vlastní účet'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = WebUser.objects.get(id=user_id)
        user.delete()
        return Response({
            'success': True,
            'message': 'Uživatel byl úspěšně smazán'
        })
    except WebUser.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Uživatel nebyl nalezen'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Informace o aktuálně přihlášeném uživateli"""
    if isinstance(request.user, AnonymousUser):
        return Response({
            'success': False,
            'message': 'Uživatel není přihlášen'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    serializer = WebUserSerializer(request.user)
    return Response({
        'success': True,
        'user': serializer.data
    })

@api_view(['POST'])
@permission_classes([])  # Povolíme přístup bez autentifikace
@csrf_exempt
def logout_view(request):
    """Odhlášení uživatele"""
    logout(request)
    return Response({'message': 'Odhlášení úspěšné'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Změna: vyžaduje autentifikaci
def current_user_view(request):
    """Získání informací o aktuálně přihlášeném uživateli"""
    if request.user.is_authenticated and not isinstance(request.user, AnonymousUser):
        user_data = WebUserSerializer(request.user).data
        print(f"Posílám data uživatele {request.user.id}: {user_data}")
        return Response({'success': True, 'user': user_data})
    else:
        return Response({'success': False, 'message': 'Uživatel není přihlášen'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def users_list_view(request):
    """Seznam všech uživatelů (pouze pro adminy)"""
    if request.user.role not in ['ADMIN', 'VEDOUCI']:
        return Response({'error': 'Nedostatečná oprávnění'}, status=status.HTTP_403_FORBIDDEN)
    
    users = WebUser.objects.all()
    serializer = WebUserSerializer(users, many=True)
    return Response({
        'success': True,
        'users': serializer.data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Získání profilu aktuálně přihlášeného uživatele"""
    serializer = WebUserProfileSerializer(request.user)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    """Aktualizace profilu aktuálně přihlášeného uživatele"""
    serializer = WebUserProfileSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        user = serializer.save()
        return Response(WebUserProfileSerializer(user).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """Změna hesla aktuálně přihlášeného uživatele"""
    serializer = WebUserPasswordChangeSerializer(data=request.data)
    if serializer.is_valid():
        stare_heslo = serializer.validated_data['stare_heslo']
        nove_heslo = serializer.validated_data['nove_heslo']
        
        if not request.user.check_heslo(stare_heslo):
            return Response({'error': 'Aktuální heslo je nesprávné'}, status=status.HTTP_400_BAD_REQUEST)
        
        request.user.set_heslo(nove_heslo)
        request.user.save()
        
        return Response({'message': 'Heslo bylo úspěšně změněno'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_image_view(request):
    """Získání profilového obrázku uživatele"""
    try:
        profilovy_obrazek = request.user.profilovy_obrazek
        serializer = ProfilovyObrazekSerializer(profilovy_obrazek)
        return Response(serializer.data)
    except ProfilovyObrazek.DoesNotExist:
        return Response({'message': 'Profilový obrázek neexistuje'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_profile_image_view(request):
    """Nahrání profilového obrázku"""
    if 'obrazek' not in request.FILES:
        return Response({'error': 'Nebyl vybrán žádný soubor'}, status=status.HTTP_400_BAD_REQUEST)
    
    obrazek = request.FILES['obrazek']
    
    # Kontrola typu souboru
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
    if obrazek.content_type not in allowed_types:
        return Response({'error': 'Nepodporovaný typ souboru. Povolené jsou pouze JPG, PNG a GIF'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Kontrola velikosti (max 5MB)
    if obrazek.size > 5 * 1024 * 1024:
        return Response({'error': 'Soubor je příliš velký. Maximální velikost je 5MB'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            # Smazání starého obrázku, pokud existuje
            try:
                stary_obrazek = request.user.profilovy_obrazek
                if stary_obrazek.obrazek:
                    # Smazání fyzického souboru
                    if default_storage.exists(stary_obrazek.obrazek.name):
                        default_storage.delete(stary_obrazek.obrazek.name)
                stary_obrazek.delete()
            except ProfilovyObrazek.DoesNotExist:
                pass
            
            # Vytvoření nového obrázku
            profilovy_obrazek = ProfilovyObrazek(uzivatel=request.user, obrazek=obrazek)
            profilovy_obrazek.save()
            
            serializer = ProfilovyObrazekSerializer(profilovy_obrazek)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        return Response({'error': f'Chyba při nahrávání obrázku: {str(e)}'}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_profile_image_view(request):
    """Smazání profilového obrázku"""
    try:
        profilovy_obrazek = request.user.profilovy_obrazek
        
        # Smazání fyzického souboru
        if profilovy_obrazek.obrazek:
            if default_storage.exists(profilovy_obrazek.obrazek.name):
                default_storage.delete(profilovy_obrazek.obrazek.name)
        
        profilovy_obrazek.delete()
        return Response({'message': 'Profilový obrázek byl smazán'})
        
    except ProfilovyObrazek.DoesNotExist:
        return Response({'error': 'Profilový obrázek neexistuje'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_user_view(request):
    """Vytvoření nového uživatele (pouze pro adminy)"""
    if request.user.role != 'ADMIN':
        return Response({'success': False, 'message': 'Nedostatečná oprávnění'}, status=status.HTTP_403_FORBIDDEN)
    
    serializer = WebUserCreateSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'success': True,
            'message': 'Uživatel byl úspěšně vytvořen',
            'user': WebUserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'success': False,
        'message': 'Chyba při vytváření uživatele',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_view(request, user_id):
    """Aktualizace uživatele (pouze pro adminy)"""
    if request.user.role != 'ADMIN':
        return Response({'success': False, 'message': 'Nedostatečná oprávnění'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = WebUser.objects.get(id=user_id)
    except WebUser.DoesNotExist:
        return Response({'success': False, 'message': 'Uživatel nenalezen'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = WebUserUpdateSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'success': True,
            'message': 'Uživatel byl úspěšně aktualizován',
            'user': WebUserSerializer(user).data
        })
    return Response({
        'success': False,
        'message': 'Chyba při aktualizaci uživatele',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user_view(request, user_id):
    """Smazání uživatele (pouze pro adminy)"""
    if request.user.role != 'ADMIN':
        return Response({'success': False, 'message': 'Nedostatečná oprávnění'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = WebUser.objects.get(id=user_id)
        user.delete()
        return Response({'success': True, 'message': 'Uživatel byl úspěšně smazán'})
    except WebUser.DoesNotExist:
        return Response({'success': False, 'message': 'Uživatel nenalezen'}, status=status.HTTP_404_NOT_FOUND)
