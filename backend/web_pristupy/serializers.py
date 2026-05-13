"""
Serializers pro modul web_pristupy
"""

from rest_framework import serializers
from .models import WEB_PRISTUPY_PRODEJNY

class WebPristupyProdejnySerializer(serializers.ModelSerializer):
    """Hlavní serializer pro přístupy prodejen"""
    
    masked_password = serializers.ReadOnlyField()  # Pro bezpečné zobrazení
    
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
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_used', 'masked_password']
    
    def validate_website_url(self, value):
        """Validace URL adresy"""
        if value and not value.startswith(('http://', 'https://')):
            value = 'https://' + value
        return value
    
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
    """Detailní serializer pro zobrazení konkrétního přístupu"""
    
    masked_password = serializers.ReadOnlyField()
    
    class Meta:
        model = WEB_PRISTUPY_PRODEJNY
        fields = '__all__'
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