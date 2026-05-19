from rest_framework import serializers
from .models import WebUser, ProfilovyObrazek
from .utils import create_web_user_with_auto_id
from stores.models import Prodejna

class WebUserSerializer(serializers.ModelSerializer):
    """Serializer pro zobrazení uživatelů (bez hesla)"""
    prodejna = serializers.SerializerMethodField()
    
    class Meta:
        model = WebUser
        fields = ['id', 'uzivatelske_jmeno', 'jmeno', 'prijmeni', 'role', 'aktivni', 'moduly', 'datum_vytvoreni',
                 'telefon', 'email', 'adresa', 'poznamka', 'prodejna_id', 'prodejna', 'technik_id']
        read_only_fields = ['datum_vytvoreni']
    
    def get_prodejna(self, obj):
        """Vrátí název prodejny podle prodejna_id"""
        if obj.prodejna_id:
            try:
                store = Prodejna.objects.get(id=obj.prodejna_id)
                return store.nazev
            except Prodejna.DoesNotExist:
                return None
        return None


class WebUserProfileSerializer(serializers.ModelSerializer):
    """Serializer pro profil uživatele (včetně možnosti úpravy)"""
    
    class Meta:
        model = WebUser
        fields = ['id', 'uzivatelske_jmeno', 'jmeno', 'prijmeni', 'telefon', 'email', 'adresa', 'poznamka', 'prodejna_id']
        read_only_fields = ['id', 'uzivatelske_jmeno']


class WebUserPasswordChangeSerializer(serializers.Serializer):
    """Serializer pro změnu hesla"""
    stare_heslo = serializers.CharField(write_only=True)
    nove_heslo = serializers.CharField(write_only=True, min_length=6)
    potvrzeni_hesla = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['nove_heslo'] != attrs['potvrzeni_hesla']:
            raise serializers.ValidationError("Nová hesla se neshodují")
        return attrs


class ProfilovyObrazekSerializer(serializers.ModelSerializer):
    """Serializer pro profilový obrázek"""
    
    class Meta:
        model = ProfilovyObrazek
        fields = ['id', 'obrazek', 'datum_nahrani']
        read_only_fields = ['datum_nahrani']


class WebUserCreateSerializer(serializers.ModelSerializer):
    """Serializer pro vytvoření nového uživatele (pouze pro adminy)"""
    id = serializers.IntegerField(read_only=True)
    heslo = serializers.CharField(write_only=True, min_length=6)
    technik_id = serializers.IntegerField(required=True, min_value=0)
    
    class Meta:
        model = WebUser
        fields = ['id', 'uzivatelske_jmeno', 'jmeno', 'prijmeni', 'heslo', 'role', 'aktivni', 'moduly',
                 'telefon', 'email', 'adresa', 'poznamka', 'prodejna_id', 'technik_id']
    
    def create(self, validated_data):
        heslo = validated_data.pop('heslo')
        validated_data.pop('id', None)
        return create_web_user_with_auto_id(validated_data, heslo)


class WebUserUpdateSerializer(serializers.ModelSerializer):
    """Serializer pro aktualizaci uživatele (pouze pro adminy)"""
    nove_heslo = serializers.CharField(write_only=True, required=False, min_length=6)
    # Alias pro zpětnou kompatibilitu s frontendem
    heslo = serializers.CharField(write_only=True, required=False, min_length=6)
    technik_id = serializers.IntegerField(required=False, min_value=0)
    
    class Meta:
        model = WebUser
        fields = ['id', 'uzivatelske_jmeno', 'jmeno', 'prijmeni', 'role', 'aktivni', 'moduly',
                 'telefon', 'email', 'adresa', 'poznamka', 'nove_heslo', 'heslo', 'prodejna_id', 'technik_id']
        read_only_fields = ['id']
    
    def update(self, instance, validated_data):
        # Přijmeme buď 'nove_heslo' nebo alias 'heslo'
        nove_heslo = validated_data.pop('nove_heslo', None) or validated_data.pop('heslo', None)
        if nove_heslo:
            instance.set_heslo(nove_heslo)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

class LoginSerializer(serializers.Serializer):
    """Serializer pro přihlášení"""
    uzivatelske_jmeno = serializers.CharField(label="Uživatelské jméno")
    heslo = serializers.CharField(label="Heslo", write_only=True)
    
    def validate(self, data):
        # Podpora aliasu "username" a ořezání whitespace
        raw_username = data.get('uzivatelske_jmeno') or data.get('username')
        heslo = (data.get('heslo') or '').strip()

        if not raw_username or not heslo:
            raise serializers.ValidationError("Uživatelské jméno a heslo jsou povinné.")

        uzivatelske_jmeno = raw_username.strip()

        # Case-insensitive lookup + tolerance na whitespace
        try:
            user = WebUser.objects.get(uzivatelske_jmeno__iexact=uzivatelske_jmeno)
        except WebUser.DoesNotExist:
            raise serializers.ValidationError("Neplatné přihlašovací údaje.")

        if not user.aktivni:
            raise serializers.ValidationError("Uživatel není aktivní.")

        if not user.check_heslo(heslo):
            raise serializers.ValidationError("Neplatné přihlašovací údaje.")

        data['user'] = user
        # Zpětně sjednotíme klíč
        data['uzivatelske_jmeno'] = user.uzivatelske_jmeno
        return data