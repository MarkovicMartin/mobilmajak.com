from rest_framework import serializers
from .models import Order, OrderStatusHistory
from users.models import WebUser


class WebUserSimpleSerializer(serializers.ModelSerializer):
    """Jednoduchý serializer pro uživatele"""
    class Meta:
        model = WebUser
        fields = ['id', 'jmeno']


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer pro historii změn stavů"""
    uzivatel = WebUserSimpleSerializer(read_only=True)
    puvodni_status_display = serializers.CharField(source='get_puvodni_status_display', read_only=True)
    novy_status_display = serializers.CharField(source='get_novy_status_display', read_only=True)
    doba_ve_stavu_text = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'puvodni_status', 'puvodni_status_display',
            'novy_status', 'novy_status_display', 'datum_zmeny',
            'uzivatel', 'poznamka', 'doba_ve_stavu_text'
        ]
    
    def get_doba_ve_stavu_text(self, obj):
        """Převede dobu ve stavu na čitelný text"""
        doba = obj.doba_ve_stavu
        if doba:
            dny = doba.days
            hodiny = doba.seconds // 3600
            minuty = (doba.seconds % 3600) // 60
            
            if dny > 0:
                return f"{dny}d {hodiny}h {minuty}m"
            elif hodiny > 0:
                return f"{hodiny}h {minuty}m"
            else:
                return f"{minuty}m"
        return None


class OrderSerializer(serializers.ModelSerializer):
    """Hlavní serializer pro objednávky"""
    zalozil = WebUserSimpleSerializer(read_only=True)
    posledni_zmena_uzivatel = WebUserSimpleSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    historie_stavu = OrderStatusHistorySerializer(many=True, read_only=True)
    celkova_doba_procesu_text = serializers.SerializerMethodField()
    doba_od_vytvoreni = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'jmeno_zakaznika', 'prijmeni_zakaznika', 'telefon_zakaznika',
            'typ_telefonu', 'dil', 'barva', 'status', 'status_display',
            'datum_vytvoreni', 'datum_aktualizace', 'zalozil', 'posledni_zmena_uzivatel',
            'poznamka', 'cena', 'dodavatel', 'servisni_cislo',
            'historie_stavu', 'celkova_doba_procesu_text', 'doba_od_vytvoreni'
        ]
        read_only_fields = ['datum_vytvoreni', 'datum_aktualizace']
    
    def get_celkova_doba_procesu_text(self, obj):
        """Převede celkovou dobu procesu na čitelný text"""
        doba = obj.celkova_doba_procesu
        if doba:
            dny = doba.days
            hodiny = doba.seconds // 3600
            minuty = (doba.seconds % 3600) // 60
            
            if dny > 0:
                return f"{dny} dnů {hodiny}h {minuty}m"
            elif hodiny > 0:
                return f"{hodiny}h {minuty}m"
            else:
                return f"{minuty} minut"
        return None
    
    def get_doba_od_vytvoreni(self, obj):
        """Doba od vytvoření objednávky"""
        from django.utils import timezone
        doba = timezone.now() - obj.datum_vytvoreni
        dny = doba.days
        hodiny = doba.seconds // 3600
        
        if dny > 0:
            return f"{dny} dnů"
        elif hodiny > 0:
            return f"{hodiny} hodin"
        else:
            minuty = doba.seconds // 60
            return f"{minuty} minut"


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer pro vytváření nových objednávek"""
    
    class Meta:
        model = Order
        fields = [
            'jmeno_zakaznika', 'prijmeni_zakaznika', 'telefon_zakaznika',
            'typ_telefonu', 'dil', 'barva', 'poznamka', 'cena', 
            'dodavatel', 'servisni_cislo'
        ]
    
    def create(self, validated_data):
        """Vytvoří novou objednávku a nastaví aktuálního uživatele jako zakladatele"""
        request = self.context.get('request')
        validated_data['zalozil'] = request.user
        validated_data['posledni_zmena_uzivatel'] = request.user
        
        # Vytvoříme objednávku
        order = Order.objects.create(**validated_data)
        
        # Vytvoříme první záznam v historii
        OrderStatusHistory.objects.create(
            objednavka=order,
            puvodni_status='',  # Prázdný - první stav
            novy_status='nove',
            uzivatel=request.user,
            poznamka='Objednávka byla vytvořena'
        )
        
        return order


class OrderUpdateStatusSerializer(serializers.Serializer):
    """Serializer pro změnu stavu objednávky"""
    novy_status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    poznamka = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        """Aktualizuje stav objednávky a vytvoří záznam v historii"""
        request = self.context.get('request')
        puvodni_status = instance.status
        novy_status = validated_data['novy_status']
        poznamka = validated_data.get('poznamka', '')
        
        if puvodni_status != novy_status:
            # Aktualizujeme objednávku
            instance.status = novy_status
            instance.posledni_zmena_uzivatel = request.user
            instance.save()
            
            # Vytvoříme záznam v historii
            OrderStatusHistory.objects.create(
                objednavka=instance,
                puvodni_status=puvodni_status,
                novy_status=novy_status,
                uzivatel=request.user,
                poznamka=poznamka
            )
        
        return instance 