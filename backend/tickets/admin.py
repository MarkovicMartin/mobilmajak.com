from django.contrib import admin
from .models import Ticket, TicketImage, TicketComment


class TicketImageInline(admin.TabularInline):
    model = TicketImage
    extra = 0


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'nazev', 'stav', 'autor_jmeno', 'vytvoreno']
    list_filter = ['stav']
    search_fields = ['nazev', 'popis', 'autor_jmeno']
    inlines = [TicketImageInline, TicketCommentInline]


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'ticket', 'autor_jmeno', 'vytvoreno']
