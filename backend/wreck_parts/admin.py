from django.contrib import admin

from .models import WreckPart


@admin.register(WreckPart)
class WreckPartAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'part_type', 'quantity', 'store', 'is_active')
    list_filter = ('store', 'part_type', 'is_active')
    search_fields = ('model_name', 'part_type', 'notes')
