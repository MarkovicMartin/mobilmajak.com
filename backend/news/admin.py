from django.contrib import admin
from .models import Novinka, NovinkaSoubor, Reakce, Komentar, KomentarSoubor

@admin.register(Novinka)
class NovinkaAdmin(admin.ModelAdmin):
    list_display = ['id', 'autor', 'obsah_preview', 'datum_vytvoreni', 'aktivni', 'pocet_reakci', 'pocet_komentaru']
    list_filter = ['aktivni', 'datum_vytvoreni', 'autor__role']
    search_fields = ['obsah', 'autor__jmeno', 'autor__prijmeni']
    readonly_fields = ['datum_vytvoreni', 'datum_upravy']
    date_hierarchy = 'datum_vytvoreni'
    
    def obsah_preview(self, obj):
        return obj.obsah[:100] + '...' if len(obj.obsah) > 100 else obj.obsah
    obsah_preview.short_description = 'Obsah'
    
    def pocet_reakci(self, obj):
        return obj.pocet_reakci
    pocet_reakci.short_description = 'Reakce'
    
    def pocet_komentaru(self, obj):
        return obj.pocet_komentaru
    pocet_komentaru.short_description = 'Komentáře'

@admin.register(NovinkaSoubor)
class NovinkaSouborAdmin(admin.ModelAdmin):
    list_display = ['id', 'novinka', 'nazev', 'typ', 'velikost', 'datum_nahrani']
    list_filter = ['typ', 'datum_nahrani']
    search_fields = ['nazev', 'novinka__obsah']
    readonly_fields = ['velikost', 'datum_nahrani']

@admin.register(Reakce)
class ReakceAdmin(admin.ModelAdmin):
    list_display = ['id', 'novinka', 'uzivatel', 'typ', 'datum_vytvoreni']
    list_filter = ['typ', 'datum_vytvoreni']
    search_fields = ['uzivatel__jmeno', 'uzivatel__prijmeni', 'novinka__obsah']
    readonly_fields = ['datum_vytvoreni']

@admin.register(Komentar)
class KomentarAdmin(admin.ModelAdmin):
    list_display = ['id', 'novinka', 'autor', 'obsah_preview', 'datum_vytvoreni', 'aktivni']
    list_filter = ['aktivni', 'datum_vytvoreni', 'autor__role']
    search_fields = ['obsah', 'autor__jmeno', 'autor__prijmeni', 'novinka__obsah']
    readonly_fields = ['datum_vytvoreni', 'datum_upravy']
    
    def obsah_preview(self, obj):
        return obj.obsah[:100] + '...' if len(obj.obsah) > 100 else obj.obsah
    obsah_preview.short_description = 'Obsah'

@admin.register(KomentarSoubor)
class KomentarSouborAdmin(admin.ModelAdmin):
    list_display = ['id', 'komentar', 'nazev', 'typ', 'velikost', 'datum_nahrani']
    list_filter = ['typ', 'datum_nahrani']
    search_fields = ['nazev', 'komentar__obsah']
    readonly_fields = ['velikost', 'datum_nahrani']
