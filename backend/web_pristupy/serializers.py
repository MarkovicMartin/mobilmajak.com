"""
Serializers pro modul web_pristupy
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from rest_framework import serializers

from .models import WEB_PRISTUPY_PRODEJNY
from .permissions import is_admin_category, is_admin_user


def normalize_website_url(value):
    """Doplní https:// a ověří formát. Prázdné nechá prázdné."""
    value = (value or '').strip()
    if not value:
        return ''
    if not value.startswith(('http://', 'https://')):
        value = 'https://' + value
    try:
        URLValidator()(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError('Neplatná URL adresa') from exc
    return value


class WebPristupyProdejnySerializer(serializers.ModelSerializer):
    """Hlavní serializer pro přístupy prodejen"""

    masked_password = serializers.ReadOnlyField()  # Pro bezpečné zobrazení
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # CharField místo URLField — jinak DRF odmítne „example.cz“ dřív, než doplníme schéma
    website_url = serializers.CharField(required=False, allow_blank=True, max_length=500)

    class Meta:
        model = WEB_PRISTUPY_PRODEJNY
        fields = [
            'id',
            'company_name',
            'website_url',
            'username',
            'password',
            'masked_password',
            'category',
            'store',
            'description',
            'notes',
            'added_by',
            'last_used',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_used', 'masked_password', 'added_by']

    def validate_website_url(self, value):
        return normalize_website_url(value)

    def validate_company_name(self, value):
        """Validace názvu společnosti"""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Název společnosti musí mít alespoň 2 znaky")
        return value.strip()

    def validate_store(self, value):
        """Validace prodejny"""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Prodejna musí být vyplněna")
        return value.strip()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        password = attrs.get('password', None)
        if self.instance is None:
            if not (password or '').strip():
                raise serializers.ValidationError({'password': 'Heslo je povinné'})
        elif password is not None and not str(password).strip():
            # Prázdné heslo při úpravě = ponechat stávající
            attrs.pop('password', None)

        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        new_category = attrs.get('category', getattr(self.instance, 'category', None))
        if is_admin_category(new_category) and not is_admin_user(user):
            raise serializers.ValidationError({
                'category': 'Kategorii Admin mohou spravovat jen administrátoři'
            })
        if self.instance and is_admin_category(self.instance.category) and not is_admin_user(user):
            raise serializers.ValidationError({
                'category': 'Kategorii Admin mohou spravovat jen administrátoři'
            })
        return attrs

    def update(self, instance, validated_data):
        if 'password' in validated_data and not str(validated_data.get('password') or '').strip():
            validated_data.pop('password')
        return super().update(instance, validated_data)
class WebPristupyProdejnyListSerializer(serializers.ModelSerializer):
    """Zjednodušený serializer pro seznam přístupů (bez hesla)"""
    
    masked_password = serializers.ReadOnlyField()
    
    class Meta:
        model = WEB_PRISTUPY_PRODEJNY
        fields = [
            'id',
            'company_name',
            'website_url',
            'username', 
            'masked_password',
            'category',
            'store',
            'description',
            'last_used',
            'is_active',
            'added_by'
        ]

class WebPristupyProdejnyDetailSerializer(serializers.ModelSerializer):
    """Detailní serializer pro zobrazení konkrétního přístupu (bez hesla v odpovědi)"""
    
    masked_password = serializers.ReadOnlyField()
    
    class Meta:
        model = WEB_PRISTUPY_PRODEJNY
        fields = [
            'id',
            'company_name',
            'website_url',
            'username',
            'masked_password',
            'category',
            'store',
            'description',
            'notes',
            'added_by',
            'last_used',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_used', 'masked_password']

class StoreStatsSerializer(serializers.Serializer):
    """Serializer pro statistiky prodejen"""
    
    store = serializers.CharField()
    count = serializers.IntegerField()
    
class AccessPasswordSerializer(serializers.Serializer):
    """Serializer pro bezpečné získání hesla"""
    
    access_id = serializers.IntegerField()
    password = serializers.CharField(read_only=True)
    
    def validate_access_id(self, value):
        """Ověří, že přístup existuje"""
        try:
            WEB_PRISTUPY_PRODEJNY.objects.get(id=value, is_active=True)
        except WEB_PRISTUPY_PRODEJNY.DoesNotExist:
            raise serializers.ValidationError("Přístup neexistuje nebo není aktivní")
        return value 