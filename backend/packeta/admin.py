from django.contrib import admin

from .models import PacketaProvizePolozka


@admin.register(PacketaProvizePolozka)
class PacketaProvizePolozkaAdmin(admin.ModelAdmin):
    list_display = ('cas', 'prodejna_id', 'zasilka', 'typ_provize', 'castka', 'import_batch')
    list_filter = ('prodejna_id', 'typ_provize')
    search_fields = ('zasilka',)
    ordering = ('-cas',)
