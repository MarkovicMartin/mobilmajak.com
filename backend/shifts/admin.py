from django.contrib import admin
from .models import Smena, SmenaDochazka, SmenaStatistiky

@admin.register(Smena)
class SmenaAdmin(admin.ModelAdmin):
    list_display = ['user', 'prodejna', 'datum', 'cas_od', 'cas_do', 'typ_smeny', 'delka_smeny_hodin', 'je_domaci_prodejna', 'aktivni']
    list_filter = ['prodejna', 'typ_smeny', 'datum', 'aktivni', 'vytvoreno']
    search_fields = ['user__jmeno', 'user__id', 'prodejna', 'poznamka']
    date_hierarchy = 'datum'
    ordering = ['-datum', 'cas_od']
    readonly_fields = ['vytvoreno', 'upraveno', 'delka_smeny_hodin', 'je_domaci_prodejna']
    
    fieldsets = (
        ('Základní informace', {
            'fields': ('user', 'prodejna', 'datum', 'typ_smeny')
        }),
        ('Časové údaje', {
            'fields': ('cas_od', 'cas_do', 'delka_smeny_hodin')
        }),
        ('Dodatečné informace', {
            'fields': ('poznamka', 'aktivni', 'je_domaci_prodejna')
        }),
        ('Systémové informace', {
            'fields': ('vytvoreno', 'upraveno'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(SmenaDochazka)
class SmenaDochazkaAdmin(admin.ModelAdmin):
    list_display = ['smena', 'typ_akce', 'cas', 'poznamka']
    list_filter = ['typ_akce', 'cas', 'smena__prodejna']
    search_fields = ['smena__user__jmeno', 'smena__user__id', 'poznamka']
    date_hierarchy = 'cas'
    ordering = ['-cas']
    readonly_fields = ['vytvoreno']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('smena__user')


@admin.register(SmenaStatistiky)
class SmenaStatistikyAdmin(admin.ModelAdmin):
    list_display = ['user', 'mesic', 'pocet_hodin_naplanovanych', 'pocet_hodin_odpracovanych', 'pocet_hodin_dovolene', 'pocet_presasu']
    list_filter = ['mesic', 'posledni_aktualizace']
    search_fields = ['user__jmeno', 'user__id']
    date_hierarchy = 'mesic'
    ordering = ['-mesic', 'user__jmeno']
    readonly_fields = ['posledni_aktualizace']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
