from django.contrib import admin
from .models import Prodejna

@admin.register(Prodejna)
class ProdejnaAdmin(admin.ModelAdmin):
    """Admin interface pro prodejny"""
    
    list_display = [
        'nazev', 
        'nazev_kratkiy', 
        'nazev_google_sheets',
        'vedouci_prodejny',
        'aktivni', 
        'poradi',
        'barva_preview'
    ]
    
    list_filter = [
        'aktivni',
        'datum_vytvoreni',
        'datum_upravy'
    ]
    
    search_fields = [
        'nazev',
        'nazev_kratkiy', 
        'nazev_google_sheets',
        'adresa',
        'vedouci_prodejny'
    ]
    
    ordering = ['poradi', 'nazev']
    
    fieldsets = (
        ('Základní informace', {
            'fields': ('nazev', 'nazev_kratkiy', 'nazev_google_sheets', 'poradi', 'aktivni')
        }),
        ('Kontaktní údaje', {
            'fields': ('adresa', 'telefon', 'email'),
            'classes': ('collapse',)
        }),
        ('Provozní informace', {
            'fields': ('otevreno_od', 'otevreno_do', 'vedouci_prodejny'),
            'classes': ('collapse',)
        }),
        ('Nastavení vzhledu', {
            'fields': ('barva',),
            'classes': ('collapse',)
        }),
        ('Poznámky', {
            'fields': ('poznamka',),
            'classes': ('collapse',)
        }),
    )
    
    def barva_preview(self, obj):
        """Zobrazí náhled barvy v admin interface"""
        if obj.barva:
            return f'<div style="width: 20px; height: 20px; background-color: {obj.barva}; border: 1px solid #ccc; display: inline-block;"></div> {obj.barva}'
        return '-'
    barva_preview.short_description = 'Barva'
    barva_preview.allow_tags = True
    
    def get_readonly_fields(self, request, obj=None):
        """Datum vytvoření a úpravy jsou read-only"""
        readonly_fields = ['datum_vytvoreni', 'datum_upravy']
        
        # Pokud editujeme existující objekt, zobraz časové údaje
        if obj:
            return readonly_fields
        return []
    
    def get_fieldsets(self, request, obj=None):
        """Přidá časové údaje do fieldsets při editaci"""
        fieldsets = super().get_fieldsets(request, obj)
        
        if obj:  # Pokud editujeme existující objekt
            fieldsets = fieldsets + (
                ('Časové údaje', {
                    'fields': ('datum_vytvoreni', 'datum_upravy'),
                    'classes': ('collapse',)
                }),
            )
        
        return fieldsets
    
    actions = ['aktivovat_prodejny', 'deaktivovat_prodejny']
    
    def aktivovat_prodejny(self, request, queryset):
        """Hromadně aktivuje prodejny"""
        count = queryset.update(aktivni=True)
        self.message_user(request, f'Aktivováno {count} prodejen.')
    aktivovat_prodejny.short_description = "Aktivovat vybrané prodejny"
    
    def deaktivovat_prodejny(self, request, queryset):
        """Hromadně deaktivuje prodejny"""
        count = queryset.update(aktivni=False)
        self.message_user(request, f'Deaktivováno {count} prodejen.')
    deaktivovat_prodejny.short_description = "Deaktivovat vybrané prodejny"
