from django.contrib import admin

from .models import (
    FinanceAuditLog,
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
    list_display = ('nazev', 'poradi', 'aktivni')
    ordering = ('poradi', 'nazev')


@admin.register(NakladPolozka)
class NakladPolozkaAdmin(admin.ModelAdmin):
    list_display = ('datum', 'castka', 'stav', 'zdroj', 'kategorie', 'prodejna_id')
    list_filter = ('stav', 'zdroj')
    search_fields = ('popis', 'protiucet', 'zprava', 'fio_id')


@admin.register(FioKategorizacniPravidlo)
class FioKategorizacniPravidloAdmin(admin.ModelAdmin):
    list_display = ('id', 'protiucet', 'zprava_obsahuje', 'kategorie', 'ignorovat', 'aktivni')
