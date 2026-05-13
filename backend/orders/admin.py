from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Order, OrderStatusHistory


class OrderStatusHistoryInline(admin.TabularInline):
    """Inline pro zobrazení historie v detailu objednávky"""
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['datum_zmeny', 'uzivatel', 'doba_ve_stavu_display']
    can_delete = False
    
    def doba_ve_stavu_display(self, obj):
        """Zobrazí dobu ve stavu v čitelném formátu"""
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
        return "-"
    doba_ve_stavu_display.short_description = "Doba ve stavu"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin pro objednávky"""
    list_display = [
        'id', 'zakaznik_display', 'typ_telefonu', 'dil', 
        'status_display', 'zalozil', 'datum_vytvoreni_display', 
        'doba_od_vytvoreni_display'
    ]
    list_filter = ['status', 'datum_vytvoreni', 'zalozil', 'typ_telefonu']
    search_fields = [
        'jmeno_zakaznika', 'prijmeni_zakaznika', 'telefon_zakaznika',
        'typ_telefonu', 'dil', 'servisni_cislo'
    ]
    readonly_fields = [
        'datum_vytvoreni', 'datum_aktualizace', 'celkova_doba_procesu_display',
        'doba_od_vytvoreni_display'
    ]
    
    fieldsets = (
        ('Zákazník', {
            'fields': ('jmeno_zakaznika', 'prijmeni_zakaznika', 'telefon_zakaznika', 'servisni_cislo')
        }),
        ('Díl/Produkt', {
            'fields': ('typ_telefonu', 'dil', 'barva', 'cena', 'dodavatel')
        }),
        ('Stav a workflow', {
            'fields': ('status', 'zalozil', 'posledni_zmena_uzivatel')
        }),
        ('Metadata', {
            'fields': ('datum_vytvoreni', 'datum_aktualizace', 'celkova_doba_procesu_display', 'doba_od_vytvoreni_display'),
            'classes': ('collapse',)
        }),
        ('Poznámky', {
            'fields': ('poznamka',)
        })
    )
    
    inlines = [OrderStatusHistoryInline]
    
    def zakaznik_display(self, obj):
        """Zobrazí jméno zákazníka a telefon"""
        return f"{obj.jmeno_zakaznika} {obj.prijmeni_zakaznika}\n{obj.telefon_zakaznika}"
    zakaznik_display.short_description = "Zákazník"
    
    def status_display(self, obj):
        """Barevné zobrazení stavu"""
        colors = {
            'nove': '#ffeb3b',  # žlutá
            'objednano': '#2196f3',  # modrá
            'v_kosiku': '#ff9800',  # oranžová
            'predobjednano': '#9c27b0',  # fialová
            'neni_skladem': '#f44336',  # červená
            'storno': '#757575',  # šedá
            'dorazilo_ceka': '#4caf50',  # zelená
            'hotovo': '#8bc34a',  # světle zelená
        }
        color = colors.get(obj.status, '#e0e0e0')
        return format_html(
            '<span style="background-color: {}; color: black; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Stav"
    
    def datum_vytvoreni_display(self, obj):
        """Formátované datum vytvoření"""
        return obj.datum_vytvoreni.strftime('%d.%m.%Y %H:%M')
    datum_vytvoreni_display.short_description = "Vytvořeno"
    datum_vytvoreni_display.admin_order_field = 'datum_vytvoreni'
    
    def doba_od_vytvoreni_display(self, obj):
        """Doba od vytvoření"""
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
    doba_od_vytvoreni_display.short_description = "Doba od vytvoření"
    
    def celkova_doba_procesu_display(self, obj):
        """Celková doba procesu"""
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
        return "Probíhá..."
    celkova_doba_procesu_display.short_description = "Celková doba procesu"


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    """Admin pro historii stavů"""
    list_display = [
        'objednavka_link', 'puvodni_status_display', 'novy_status_display',
        'uzivatel', 'datum_zmeny', 'doba_ve_stavu_display'
    ]
    list_filter = ['novy_status', 'datum_zmeny', 'uzivatel']
    search_fields = [
        'objednavka__jmeno_zakaznika', 'objednavka__prijmeni_zakaznika',
        'objednavka__typ_telefonu', 'uzivatel__jmeno'
    ]
    readonly_fields = ['datum_zmeny', 'doba_ve_stavu_display']
    
    def objednavka_link(self, obj):
        """Link na detail objednávky"""
        url = reverse('admin:orders_order_change', args=[obj.objednavka.pk])
        return format_html('<a href="{}">{}</a>', url, str(obj.objednavka))
    objednavka_link.short_description = "Objednávka"
    
    def puvodni_status_display(self, obj):
        """Barevné zobrazení původního stavu"""
        if not obj.puvodni_status:
            return "-"
        return format_html(
            '<span style="background-color: #e0e0e0; padding: 2px 6px; border-radius: 3px;">{}</span>',
            obj.get_puvodni_status_display()
        )
    puvodni_status_display.short_description = "Původní stav"
    
    def novy_status_display(self, obj):
        """Barevné zobrazení nového stavu"""
        colors = {
            'nove': '#ffeb3b',
            'objednano': '#2196f3',
            'v_kosiku': '#ff9800',
            'predobjednano': '#9c27b0',
            'neni_skladem': '#f44336',
            'storno': '#757575',
            'dorazilo_ceka': '#4caf50',
            'hotovo': '#8bc34a',
        }
        color = colors.get(obj.novy_status, '#e0e0e0')
        return format_html(
            '<span style="background-color: {}; color: black; padding: 2px 6px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_novy_status_display()
        )
    novy_status_display.short_description = "Nový stav"
    
    def doba_ve_stavu_display(self, obj):
        """Zobrazí dobu ve stavu v čitelném formátu"""
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
        return "-"
    doba_ve_stavu_display.short_description = "Doba ve stavu" 