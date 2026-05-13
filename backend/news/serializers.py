from rest_framework import serializers
from .models import Novinka, NovinkaSoubor, Reakce, Komentar, KomentarSoubor, Kategorie
from users.models import WebUser

class WebUserSerializer(serializers.ModelSerializer):
    """Serializer pro zobrazení informací o uživateli"""
    inicialy = serializers.SerializerMethodField()
    
    class Meta:
        model = WebUser
        fields = ['id', 'jmeno', 'prijmeni', 'uzivatelske_jmeno', 'inicialy']
    
    def get_inicialy(self, obj):
        """Vrátí iniciály uživatele pro avatar"""
        return f"{obj.jmeno[0]}{obj.prijmeni[0]}" if obj.jmeno and obj.prijmeni else "U"

class KategorieSerializer(serializers.ModelSerializer):
    """Serializer pro kategorie"""
    
    class Meta:
        model = Kategorie
        fields = ['id', 'nazev', 'barva', 'ikona', 'datum_vytvoreni']

class NovinkaSouborSerializer(serializers.ModelSerializer):
    """Serializer pro soubory novinek"""
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = NovinkaSoubor
        fields = ['id', 'nazev', 'typ', 'velikost', 'url', 'datum_nahrani']
    
    def get_url(self, obj):
        """Vrátí URL souboru"""
        if obj.soubor:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.soubor.url)
        return None

class KomentarSouborSerializer(serializers.ModelSerializer):
    """Serializer pro soubory komentářů"""
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = KomentarSoubor
        fields = ['id', 'nazev', 'typ', 'velikost', 'url', 'datum_nahrani']
    
    def get_url(self, obj):
        """Vrátí URL souboru"""
        if obj.soubor:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.soubor.url)
        return None

class ReakceSerializer(serializers.ModelSerializer):
    """Serializer pro reakce"""
    uzivatel = WebUserSerializer(read_only=True)
    
    class Meta:
        model = Reakce
        fields = ['id', 'typ', 'uzivatel', 'datum_vytvoreni']

class KomentarSerializer(serializers.ModelSerializer):
    """Serializer pro komentáře"""
    autor = WebUserSerializer(read_only=True)
    soubory = KomentarSouborSerializer(many=True, read_only=True)
    
    class Meta:
        model = Komentar
        fields = ['id', 'obsah', 'autor', 'soubory', 'datum_vytvoreni', 'datum_upravy']

class NovinkaSerializer(serializers.ModelSerializer):
    """Serializer pro novinky"""
    autor = WebUserSerializer(read_only=True)
    soubory = NovinkaSouborSerializer(many=True, read_only=True)
    reakce = ReakceSerializer(many=True, read_only=True)
    komentare = KomentarSerializer(many=True, read_only=True)
    kategorie = KategorieSerializer(many=True, read_only=True)
    pocet_reakci = serializers.IntegerField(read_only=True)
    pocet_komentaru = serializers.IntegerField(read_only=True)
    moje_reakce = serializers.SerializerMethodField()
    muze_mazat = serializers.SerializerMethodField()
    
    class Meta:
        model = Novinka
        fields = [
            'id', 'obsah', 'autor', 'kategorie', 'soubory', 'reakce', 'komentare',
            'pocet_reakci', 'pocet_komentaru', 'moje_reakce', 'muze_mazat',
            'datum_vytvoreni', 'datum_upravy'
        ]
    
    def get_moje_reakce(self, obj):
        """Vrátí reakci aktuálního uživatele na tuto novinku"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            try:
                reakce = obj.reakce.get(uzivatel=request.user)
                return ReakceSerializer(reakce).data
            except Reakce.DoesNotExist:
                return None
        return None
    
    def get_muze_mazat(self, obj):
        """Zkontroluje, zda může aktuální uživatel mazat tuto novinku"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # Administrátor nebo autor může mazat
            return (request.user.role == 'ADMIN' or request.user == obj.autor)
        return False

class NovinkaCreateSerializer(serializers.ModelSerializer):
    """Serializer pro vytváření novinek"""
    autor = WebUserSerializer(read_only=True)
    soubory = NovinkaSouborSerializer(many=True, read_only=True)
    reakce = ReakceSerializer(many=True, read_only=True)
    komentare = KomentarSerializer(many=True, read_only=True)
    kategorie = serializers.PrimaryKeyRelatedField(many=True, queryset=Kategorie.objects.all(), required=False)
    kategorie_display = KategorieSerializer(many=True, read_only=True, source='kategorie')
    pocet_reakci = serializers.IntegerField(read_only=True)
    pocet_komentaru = serializers.IntegerField(read_only=True)
    moje_reakce = serializers.SerializerMethodField()
    muze_mazat = serializers.SerializerMethodField()
    
    class Meta:
        model = Novinka
        fields = [
            'id', 'obsah', 'kategorie', 'kategorie_display', 'autor', 'soubory', 'reakce', 'komentare',
            'pocet_reakci', 'pocet_komentaru', 'moje_reakce', 'muze_mazat',
            'datum_vytvoreni', 'datum_upravy'
        ]
    
    def create(self, validated_data):
        validated_data['autor'] = self.context['request'].user
        return super().create(validated_data)
    
    def to_representation(self, instance):
        """Přejmenovává kategorie_display zpět na kategorie pro odpověď"""
        data = super().to_representation(instance)
        data['kategorie'] = data.pop('kategorie_display', [])
        return data
    
    def get_moje_reakce(self, obj):
        """Vrátí reakci aktuálního uživatele na tuto novinku"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            try:
                reakce = obj.reakce.get(uzivatel=request.user)
                return ReakceSerializer(reakce).data
            except Reakce.DoesNotExist:
                return None
        return None
    
    def get_muze_mazat(self, obj):
        """Zkontroluje, zda může aktuální uživatel mazat tuto novinku"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # Administrátor nebo autor může mazat
            return (request.user.role == 'ADMIN' or request.user == obj.autor)
        return False

class KomentarCreateSerializer(serializers.ModelSerializer):
    """Serializer pro vytváření komentářů"""
    autor = WebUserSerializer(read_only=True)
    soubory = KomentarSouborSerializer(many=True, read_only=True)
    
    class Meta:
        model = Komentar
        fields = ['id', 'obsah', 'autor', 'soubory', 'datum_vytvoreni', 'datum_upravy']
    
    def create(self, validated_data):
        validated_data['autor'] = self.context['request'].user
        return super().create(validated_data)

class ReakceCreateSerializer(serializers.ModelSerializer):
    """Serializer pro vytváření reakcí"""
    uzivatel = WebUserSerializer(read_only=True)
    
    class Meta:
        model = Reakce
        fields = ['id', 'typ', 'uzivatel', 'datum_vytvoreni', 'novinka']
    
    def create(self, validated_data):
        validated_data['uzivatel'] = self.context['request'].user
        novinka = validated_data.get('novinka')
        
        if not novinka:
            raise serializers.ValidationError("Pole 'novinka' je povinné")
        
        # Pokud už uživatel reagoval na tuto novinku, aktualizujeme reakci
        reakce, created = Reakce.objects.update_or_create(
            novinka=novinka,
            uzivatel=validated_data['uzivatel'],
            defaults={'typ': validated_data['typ']}
        )
        return reakce 