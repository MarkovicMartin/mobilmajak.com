from rest_framework import serializers
from .models import Prodejna

class ProdejnaSerializer(serializers.ModelSerializer):
    """Serializer pro kompletní správu prodejen"""
    
    class Meta:
        model = Prodejna
        fields = [
            'id', 'nazev', 'nazev_kratkiy', 'nazev_google_sheets',
            'adresa', 'telefon', 'email', 
            'otevreno_od', 'otevreno_do', 'vedouci_prodejny',
            'aktivni', 'barva', 'poradi', 'poznamka',
            'datum_vytvoreni', 'datum_upravy'
        ]
        read_only_fields = ['datum_vytvoreni', 'datum_upravy']
    
    def to_internal_value(self, data):
        """Převede data z frontendu do správného formátu pro Django"""
        # Kopie dat pro úpravu
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        
        # Převod prázdných stringů na None pro volitelná pole
        time_fields = ['otevreno_od', 'otevreno_do']
        text_fields = ['adresa', 'telefon', 'email', 'vedouci_prodejny', 'poznamka', 'nazev_google_sheets']
        
        for field in time_fields + text_fields:
            if field in data and data[field] == '':
                data[field] = None
        
        # Zajistíme, že pořadí je číslo
        if 'poradi' in data and isinstance(data['poradi'], str):
            try:
                data['poradi'] = int(data['poradi']) if data['poradi'] else 0
            except ValueError:
                data['poradi'] = 0
        
        return super().to_internal_value(data)
    
    def validate_nazev(self, value):
        """Ověří, že název prodejny je jedinečný"""
        instance = getattr(self, 'instance', None)
        if instance:
            # Při aktualizaci - zkontroluj, že název nepoužívá jiná prodejna
            if Prodejna.objects.exclude(pk=instance.pk).filter(nazev=value).exists():
                raise serializers.ValidationError("Prodejna s tímto názvem již existuje.")
        else:
            # Při vytváření - zkontroluj, že název neexistuje
            if Prodejna.objects.filter(nazev=value).exists():
                raise serializers.ValidationError("Prodejna s tímto názvem již existuje.")
        return value
    
    def validate_poradi(self, value):
        """Ověří, že pořadí je pozitivní číslo"""
        if value < 0:
            raise serializers.ValidationError("Pořadí musí být nezáporné číslo.")
        return value
    
    def validate_barva(self, value):
        """Ověří formát hex barvy"""
        if value and not value.startswith('#'):
            raise serializers.ValidationError("Barva musí být ve formátu hex (např. #FF0000).")
        if value and len(value) != 7:
            raise serializers.ValidationError("Barva musí být 7 znaků dlouhá včetně # (např. #FF0000).")
        return value

class ProdejnaListSerializer(serializers.ModelSerializer):
    """Zjednodušený serializer pro seznam prodejen"""
    
    class Meta:
        model = Prodejna
        fields = [
            'id', 'nazev', 'nazev_kratkiy', 'aktivni', 
            'barva', 'poradi', 'vedouci_prodejny'
        ]

class ProdejnaChoiceSerializer(serializers.ModelSerializer):
    """Minimální serializer pro dropdown/choice seznamy"""
    
    class Meta:
        model = Prodejna
        fields = ['id', 'nazev', 'nazev_kratkiy'] 