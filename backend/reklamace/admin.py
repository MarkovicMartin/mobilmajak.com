from django.contrib import admin

from .models import ReklamacePolozka


@admin.register(ReklamacePolozka)
class ReklamacePolozkaAdmin(admin.ModelAdmin):
    list_display = ('nase_znacka', 'nazev_zbozi', 'status', 'dodavatel', 'datum_odeslani', 'prodejna')
    list_filter = ('status', 'prodejna', 'dodavatel')
    search_fields = ('nase_znacka', 'nazev_zbozi', 'faktura', 'ean', 'p_kod', 'cislo_zasilky')
