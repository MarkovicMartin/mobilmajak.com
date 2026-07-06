from django.contrib import admin

from .models import DailyDutyTemplate


@admin.register(DailyDutyTemplate)
class DailyDutyTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'periodicity', 'store', 'role', 'is_active')
    list_filter = ('periodicity', 'store', 'is_active')
