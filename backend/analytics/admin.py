from django.contrib import admin
from .models import ProdejniData, ProdejniDataDenni, ProdejniDataMesicni, GoogleSheetsConfig, WebProdejeAll


class BaseProdejniDataAdmin(admin.ModelAdmin):
    """Základní admin konfigurace pro prodejní data"""
    list_display = [
        'timestamp', 'prodejna', 'prodejce', 
        'polozky_nad_100', 'sluzby_celkem', 'pol_dok'
    ]
    list_filter = ['prodejna', 'timestamp']
    search_fields = ['prodejna', 'prodejce']
    ordering = ['-timestamp']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Základní informace', {
            'fields': ('timestamp', 'prodejna', 'prodejce', 'id_prodejce')
        }),
        ('Klíčové metriky', {
            'fields': ('polozky_nad_100', 'sluzby_celkem', 'pol_dok')
        }),
        ('Produkty', {
            'fields': (
                'ct300', 'ct600', 'ct1200', 'akt', 'zah250', 'nap',
                'zah500', 'kop250', 'kop500', 'pz1', 'knz', 'aligator'
            )
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(ProdejniDataDenni)
class ProdejniDataDenniAdmin(admin.ModelAdmin):
    list_display = ('uzivatel', 'datum', 'polozky_nad_100', 'sluzby_celkem')
    list_filter = ('datum', 'uzivatel__role')
    search_fields = ('uzivatel__uzivatelske_jmeno', 'uzivatel__jmeno', 'uzivatel__prijmeni')
    ordering = ('-datum', 'uzivatel__uzivatelske_jmeno')
    
    fieldsets = (
        ('Základní informace', {
            'fields': ('uzivatel', 'datum')
        }),
        ('Metriky', {
            'fields': ('polozky_nad_100', 'sluzby_celkem', 'prumer_polozek_uctu')
        }),
        ('Produkty', {
            'fields': ('ct300', 'ct600', 'ct1200', 'akt', 'zah250', 'nap', 'zah500', 'kop250', 'kop500', 'pz1', 'knz', 'aligator'),
            'classes': ('collapse',)
        }),
        ('Časové údaje', {
            'fields': ('datum_vytvoreni', 'datum_upravy'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('datum_vytvoreni', 'datum_upravy')


@admin.register(ProdejniDataMesicni)
class ProdejniDataMesicniAdmin(admin.ModelAdmin):
    list_display = ('uzivatel', 'rok', 'mesic', 'polozky_nad_100', 'sluzby_celkem')
    list_filter = ('rok', 'mesic', 'uzivatel__role')
    search_fields = ('uzivatel__uzivatelske_jmeno', 'uzivatel__jmeno', 'uzivatel__prijmeni')
    ordering = ('-rok', '-mesic', 'uzivatel__uzivatelske_jmeno')
    
    fieldsets = (
        ('Základní informace', {
            'fields': ('uzivatel', 'rok', 'mesic')
        }),
        ('Metriky', {
            'fields': ('polozky_nad_100', 'sluzby_celkem', 'prumer_polozek_uctu')
        }),
        ('Produkty', {
            'fields': ('ct300', 'ct600', 'ct1200', 'akt', 'zah250', 'nap', 'zah500', 'kop250', 'kop500', 'pz1', 'knz', 'aligator'),
            'classes': ('collapse',)
        }),
        ('Časové údaje', {
            'fields': ('datum_vytvoreni', 'datum_upravy'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('datum_vytvoreni', 'datum_upravy')


@admin.register(ProdejniData)
class ProdejniDataAdmin(admin.ModelAdmin):
    """DEPRECATED: Admin pro starý model"""
    list_display = [
        'timestamp', 'data_type', 'prodejna', 'prodejce', 
        'polozky_nad_100', 'sluzby_celkem', 'pol_dok'
    ]
    list_filter = ['data_type', 'prodejna', 'timestamp']
    search_fields = ['prodejna', 'prodejce']
    ordering = ['-timestamp']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        """Zobrazí varování o deprecated modelu"""
        return super().get_queryset(request)
    
    class Media:
        css = {
            'all': ('admin/css/deprecated.css',)
        }


@admin.register(GoogleSheetsConfig)
class GoogleSheetsConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'spreadsheet_id', 'is_active', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['name', 'spreadsheet_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Základní nastavení', {
            'fields': ('name', 'spreadsheet_id', 'is_active')
        }),
        ('Listy', {
            'fields': ('daily_sheet_name', 'monthly_sheet_name')
        }),
        ('API konfigurace', {
            'fields': ('api_key',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    ) 


# Model WebProdeje je již nepoužívaný a není registrován v adminu.


@admin.register(WebProdejeAll)
class WebProdejeAllAdmin(admin.ModelAdmin):
    """Admin rozhraní pro rozšířenou tabulku WEB_PRODEJE_ALL"""
    
    list_display = [
        'id', 'typ', 'kod', 'nazev_zkraceny', 'stredisko',
        'cena_ks_vcl_dph', 'zisk', 'marketingovy_kanal', 'kategorie'
    ]
    
    list_filter = [
        'typ', 'stredisko', 'marketingovy_kanal', 'dropshipping',
        'kategorie', 'kategorie_1', 'id_prodejny', 'technik', 'k_servisu'
    ]
    
    search_fields = [
        'kod', 'nazev', 'doklad', 'stredisko', 'kategorie', 
        'kategorie_1', 'kategorie_2', 'nazev_prodejce'
    ]
    
    ordering = ['-datum_vlozeni', '-id']
    
    readonly_fields = [
        'datum_vlozeni', 'celkova_cena', 'celkovy_zisk'
    ]
    
    list_per_page = 50
    
    fieldsets = (
        ('Základní informace', {
            'fields': ('typ', 'kod', 'nazev', 'pocet_kusu')
        }),
        ('Doklad', {
            'fields': ('doklad', 'objednavka', 'pokladna')
        }),
        ('Místo prodeje', {
            'fields': ('stredisko', 'id_prodejny', 'id_prodejce', 'spravce')
        }),
        ('Ceny a zisk', {
            'fields': (
                'cena_ks_vcl_dph', 'cena_ks_bez_dph', 'skladova_cena_bez_dph', 'zisk',
                'celkova_cena', 'celkovy_zisk'
            )
        }),
        ('Prodejní kanály', {
            'fields': ('marketingovy_kanal', 'dropshipping')
        }),
        ('Kategorie', {
            'fields': ('kategorie', 'kategorie_1', 'kategorie_2', 'kategorie_puvodni')
        }),
        ('Servis a technik', {
            'fields': ('technik', 'k_servisu')
        }),
        ('Poznámky', {
            'fields': ('poznamka', 'poznamka_zakaznika'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('datum_vlozeni',),
            'classes': ('collapse',)
        }),
    )
    
    def nazev_zkraceny(self, obj):
        """Zkrácený název pro přehlednost"""
        if obj.nazev and len(obj.nazev) > 50:
            return obj.nazev[:47] + "..."
        return obj.nazev
    nazev_zkraceny.short_description = "Název"
    
    def get_queryset(self, request):
        """Optimalizace dotazů"""
        return super().get_queryset(request).select_related()
    
    # Žádné vlastní akce prozatím