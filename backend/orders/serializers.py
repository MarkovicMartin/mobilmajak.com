from rest_framework import serializers

from .models import Order, OrderStatusHistory
from users.models import WebUser
from stores.models import Prodejna
from .slack_notify import notify_order_created
from .sla import sla_days_threshold
from .prodejna_resolve import resolve_order_prodejna
from .status_config import STATUSES_REQUIRING_DODAVATEL, RETIRED_STATUSES


class WebUserSimpleSerializer(serializers.ModelSerializer):
    """Jednoduchý serializer pro uživatele"""
    class Meta:
        model = WebUser
        fields = ['id', 'jmeno', 'prijmeni']


class ProdejnaSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prodejna
        fields = ['id', 'nazev', 'nazev_kratkiy']


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
    prodejna = ProdejnaSimpleSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    historie_stavu = OrderStatusHistorySerializer(many=True, read_only=True)
    celkova_doba_procesu_text = serializers.SerializerMethodField()
    doba_od_vytvoreni = serializers.SerializerMethodField()
    dni_ve_stavu = serializers.SerializerMethodField()
    sla_overdue = serializers.SerializerMethodField()
    sla_days_threshold = serializers.SerializerMethodField()
    symplio_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'jmeno_zakaznika', 'prijmeni_zakaznika', 'telefon_zakaznika',
            'typ_telefonu', 'dil', 'barva', 'status', 'status_display',
            'datum_vytvoreni', 'datum_aktualizace', 'zalozil', 'posledni_zmena_uzivatel',
            'prodejna', 'poznamka', 'cena', 'dodavatel', 'servisni_cislo',
            'symplio_objednavka_id', 'symplio_url',
            'historie_stavu', 'celkova_doba_procesu_text', 'doba_od_vytvoreni',
            'dni_ve_stavu', 'sla_overdue', 'sla_days_threshold',
        ]
        read_only_fields = ['datum_vytvoreni', 'datum_aktualizace', 'prodejna']
    
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

    def get_dni_ve_stavu(self, obj):
        return obj.days_in_current_status()

    def get_sla_days_threshold(self, obj):
        return sla_days_threshold()

    def get_sla_overdue(self, obj):
        if obj.status in ('hotovo', 'storno'):
            return False
        return obj.days_in_current_status() >= sla_days_threshold()

    def get_symplio_url(self, obj):
        sid = (obj.symplio_objednavka_id or '').strip()
        if not sid:
            return None
        return f"https://www.mobilmajak.cz/admin/objednavky/objednavka-{sid}"


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer pro vytváření / úpravu objednávek (stav přes update_status)."""
    servisni_cislo = serializers.CharField(required=False, allow_blank=True, max_length=50)
    jmeno_zakaznika = serializers.CharField(required=False, allow_blank=True, max_length=100)
    prijmeni_zakaznika = serializers.CharField(required=False, allow_blank=True, max_length=100)
    telefon_zakaznika = serializers.CharField(required=False, allow_blank=True, max_length=20)
    barva = serializers.CharField(required=False, allow_blank=True, max_length=50)

    class Meta:
        model = Order
        fields = [
            'jmeno_zakaznika', 'prijmeni_zakaznika', 'telefon_zakaznika',
            'typ_telefonu', 'dil', 'barva', 'poznamka', 'cena',
            'dodavatel', 'servisni_cislo', 'symplio_objednavka_id',
        ]

    def _merged(self, attrs, field):
        if field in attrs:
            return (attrs.get(field) or '').strip()
        if self.instance is not None:
            return (getattr(self.instance, field) or '').strip()
        return ''

    def validate_typ_telefonu(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Model je povinný.')
        return value

    def validate_dil(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Díl je povinný.')
        return value

    def validate_barva(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Barva je povinná.')
        return value

    def validate_servisni_cislo(self, value):
        return (value or '').strip()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Při partial update vyžaduj barvu jen když se mění nebo při create
        if self.instance is None or 'barva' in attrs:
            if not self._merged(attrs, 'barva'):
                raise serializers.ValidationError({'barva': 'Barva je povinná.'})

        serviska = self._merged(attrs, 'servisni_cislo')
        jmeno = self._merged(attrs, 'jmeno_zakaznika')
        telefon = self._merged(attrs, 'telefon_zakaznika')
        has_customer = bool(jmeno and telefon)

        if not serviska and not has_customer:
            raise serializers.ValidationError(
                'Vyplňte servisní číslo, nebo jméno a telefon zákazníka.'
            )
        return attrs

    def create(self, validated_data):
        """Vytvoří novou objednávku a nastaví aktuálního uživatele jako zakladatele"""
        request = self.context.get('request')
        validated_data['zalozil'] = request.user
        validated_data['posledni_zmena_uzivatel'] = request.user
        validated_data['prodejna'] = resolve_order_prodejna(request.user)
        validated_data.setdefault('jmeno_zakaznika', '')
        validated_data.setdefault('prijmeni_zakaznika', '')
        validated_data.setdefault('telefon_zakaznika', '')

        order = Order.objects.create(**validated_data)

        OrderStatusHistory.objects.create(
            objednavka=order,
            puvodni_status='',
            novy_status='nove',
            uzivatel=request.user,
            poznamka='Objednávka byla vytvořena'
        )

        notify_order_created(order)

        return order

    def update(self, instance, validated_data):
        request = self.context.get('request')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if request and getattr(request, 'user', None):
            instance.posledni_zmena_uzivatel = request.user
        instance.save()
        return instance


class OrderUpdateStatusSerializer(serializers.Serializer):
    """Serializer pro změnu stavu objednávky"""
    novy_status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    poznamka = serializers.CharField(required=False, allow_blank=True)
    dodavatel = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        instance = self.instance
        novy_status = attrs['novy_status']
        if novy_status in RETIRED_STATUSES:
            raise serializers.ValidationError({
                'novy_status': 'Stavy Není skladem a Storno už nejsou podporované.',
            })
        incoming = attrs.get('dodavatel', None)
        if incoming is not None:
            resolved = (incoming or '').strip()
        else:
            resolved = (instance.dodavatel or '').strip() if instance else ''

        if novy_status in STATUSES_REQUIRING_DODAVATEL and not resolved:
            raise serializers.ValidationError({
                'dodavatel': 'Dodavatel je povinný při přesunu do v košíku / objednáno.',
            })
        attrs['_resolved_dodavatel'] = resolved if incoming is not None else None
        return attrs
    
    def update(self, instance, validated_data):
        """Aktualizuje stav objednávky a vytvoří záznam v historii"""
        request = self.context.get('request')
        puvodni_status = instance.status
        novy_status = validated_data['novy_status']
        poznamka = validated_data.get('poznamka', '')
        new_dodavatel = validated_data.get('_resolved_dodavatel')

        update_fields = ['datum_aktualizace']
        if new_dodavatel is not None:
            instance.dodavatel = new_dodavatel or None
            update_fields.append('dodavatel')
        
        if puvodni_status != novy_status:
            instance.status = novy_status
            instance.posledni_zmena_uzivatel = request.user
            instance.sla_reminder_sent_at = None
            update_fields.extend([
                'status', 'posledni_zmena_uzivatel', 'sla_reminder_sent_at',
            ])
            
            OrderStatusHistory.objects.create(
                objednavka=instance,
                puvodni_status=puvodni_status,
                novy_status=novy_status,
                uzivatel=request.user,
                poznamka=poznamka
            )

        instance.save(update_fields=list(dict.fromkeys(update_fields)))
        
        return instance
