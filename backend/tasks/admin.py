from django.contrib import admin
from .models import Ukol


@admin.register(Ukol)
class UkolAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'ukol', 'priorita', 'deadline', 'stav',
        'id_prodejce_ukol', 'id_prodejce_zadal', 'id_prodejny',
        'vytvoreno'
    )
    list_filter = ('stav', 'priorita')
    search_fields = ('ukol',)


