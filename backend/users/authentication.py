from rest_framework import authentication
from rest_framework import exceptions
from django.contrib.auth.models import AnonymousUser
from .models import WebUser

class WebUserAuthentication(authentication.BaseAuthentication):
    """Vlastní autentifikace pro WebUser model"""
    
    def authenticate(self, request):
        # Pro login endpoint necháme projít bez autentifikace
        if request.path.endswith('/login/'):
            return None
        
        # Zkontrolujeme session - ošetříme případ, kdy request nemá session
        if not hasattr(request, 'session') or not request.session.get('_auth_user_id'):
            return None
        
        try:
            user_id = request.session.get('_auth_user_id')
            user = WebUser.objects.get(id=user_id)
            
            if not user.aktivni:
                return None
                
            return (user, None)
        except WebUser.DoesNotExist:
            return None
    
    def authenticate_header(self, request):
        return 'Session'

class WebUserSessionAuthentication(authentication.SessionAuthentication):
    """Vlastní session autentifikace pro WebUser model"""
    
    def authenticate(self, request):
        # Pro login endpoint necháme projít bez autentifikace
        if request.path.endswith('/login/'):
            return None
        
        # Zkontrolujeme session - ošetříme případ, kdy request nemá session
        if not hasattr(request, 'session') or not request.session.get('_auth_user_id'):
            print(f"Session neobsahuje _auth_user_id: {getattr(request, 'session', 'No session')}")
            return None
        
        try:
            user_id = request.session.get('_auth_user_id')
            print(f"Načítám uživatele s ID: {user_id}")
            user = WebUser.objects.get(id=user_id)
            
            if not user.aktivni:
                print(f"Uživatel {user_id} není aktivní")
                return None
                
            print(f"Uživatel {user_id} úspěšně načten")
            return (user, None)
        except WebUser.DoesNotExist:
            print(f"Uživatel s ID {user_id} neexistuje")
            return None
        except Exception as e:
            print(f"Chyba při načítání uživatele: {e}")
            return None 