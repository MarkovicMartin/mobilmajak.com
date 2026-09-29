from django.contrib import admin

from .models import KnowledgeDocument


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ('nazev', 'aktivni', 'nahral', 'velikost', 'vytvoreno')
    list_filter = ('aktivni',)
    search_fields = ('nazev', 'popis', 'original_filename')
    readonly_fields = ('extracted_text', 'velikost', 'original_filename', 'vytvoreno', 'upraveno')
