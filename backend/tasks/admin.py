from django.contrib import admin
from .models import Ukol, UkolKomentar


@admin.register(Ukol)
class UkolAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'ukol', 'typ', 'priorita', 'deadline', 'stav',
        'id_prodejce_ukol', 'id_prodejce_zadal', 'id_prodejny',
        'vytvoreno',
    )
    list_filter = ('stav', 'priorita', 'typ')


@admin.register(UkolKomentar)
class UkolKomentarAdmin(admin.ModelAdmin):
    list_display = ('id', 'ukol', 'autor_jmeno', 'vytvoreno')
    search_fields = ('ukol',)


