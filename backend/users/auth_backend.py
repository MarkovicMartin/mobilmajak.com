from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser
from .models import WebUser

class WebUserAuthBackend(BaseBackend):
    """Custom authentication backend pro WebUser model"""
    
    def authenticate(self, request, uzivatelske_jmeno=None, password=None, **kwargs):
        if uzivatelske_jmeno is None or password is None:
            return None
        
        try:
            user = WebUser.objects.get(uzivatelske_jmeno=uzivatelske_jmeno)
        except WebUser.DoesNotExist:
            return None
        
        if not user.aktivni:
            return None
        
        if user.check_heslo(password):
            return user
        
        return None
    
    def get_user(self, user_id):
        try:
            return WebUser.objects.get(id=user_id)
        except WebUser.DoesNotExist:
            return None 