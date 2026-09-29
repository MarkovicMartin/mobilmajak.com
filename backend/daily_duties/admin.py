from django.contrib import admin

from .models import DailyDutyCompletion, DailyDutyTemplate


@admin.register(DailyDutyTemplate)
class DailyDutyTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'periodicity', 'prodejna', 'uzivatel', 'is_active')
    list_filter = ('periodicity', 'is_active', 'prodejna')
    search_fields = ('title', 'description')


@admin.register(DailyDutyCompletion)
class DailyDutyCompletionAdmin(admin.ModelAdmin):
    list_display = ('template', 'period_start', 'completed_by', 'completed_at')
    list_filter = ('period_start',)
