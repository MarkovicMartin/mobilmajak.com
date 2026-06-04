from django.contrib import admin

from coaching.models import CoachingGoal, CoachingNote


@admin.register(CoachingNote)
class CoachingNoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'prodejce', 'autor', 'typ', 'vytvoreno']
    list_filter = ['typ']


@admin.register(CoachingGoal)
class CoachingGoalAdmin(admin.ModelAdmin):
    list_display = ['id', 'prodejce', 'nazev', 'stav', 'termin', 'vytvoreno']
    list_filter = ['stav']
