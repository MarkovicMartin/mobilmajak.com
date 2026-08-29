from django.contrib import admin

from .models import (
    FinanceAuditLog,
    FinanceDoklad,
    FinanceZustatek,
    FioKategorizacniPravidlo,
    NakladKategorie,
    NakladPolozka,
)


@admin.register(FinanceAuditLog)
class FinanceAuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'akce', 'user_id', 'ip', 'vytvoreno')
    list_filter = ('akce',)
    search_fields = ('detail', 'akce')
    readonly_fields = ('vytvoreno',)


@admin.register(NakladKategorie)
class NakladKategorieAdmin(admin.ModelAdmin):
    list_display = ('nazev', 'parent', 'typ_dph', 'poradi', 'aktivni')
    ordering = ('poradi', 'nazev')


@admin.register(NakladPolozka)
class NakladPolozkaAdmin(admin.ModelAdmin):
    list_display = (
        'datum', 'castka', 'dph_stav', 'typ_platby', 'stav', 'zdroj', 'pokladna_label',
        'kategorie', 'prodejna_id',
    )
    list_filter = ('stav', 'zdroj', 'dph_stav', 'typ_platby')
    search_fields = ('popis', 'protiucet', 'zprava', 'fio_id', 'symplio_doklad', 'pokladna_label')


@admin.register(FinanceDoklad)
class FinanceDokladAdmin(admin.ModelAdmin):
    list_display = ('id', 'dodavatel_nazev', 'cislo_faktury', 'castka_celkem', 'stav', 'vytvoreno')
    list_filter = ('stav',)


@admin.register(FinanceZustatek)
class FinanceZustatekAdmin(admin.ModelAdmin):
    list_display = ('datum', 'typ', 'label', 'castka', 'mena', 'vytvoreno')
    list_filter = ('typ',)


@admin.register(FioKategorizacniPravidlo)
class FioKategorizacniPravidloAdmin(admin.ModelAdmin):
    list_display = ('id', 'protiucet', 'zprava_obsahuje', 'text_shoda', 'kategorie', 'ignorovat', 'aktivni')
