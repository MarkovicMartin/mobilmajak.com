from django.contrib import admin
from .models import PlanMonth, PlanStore, PlanCategory


class PlanStoreInline(admin.TabularInline):
    model = PlanStore
    extra = 0
    fields = ('prodejna', 'podil_procenta', 'castka_prodejna', 'castka_prodej', 'castka_servis', 'zamknuto')


class PlanCategoryInline(admin.TabularInline):
    model = PlanCategory
    extra = 0
    fields = ('kategorie_kod', 'podil_procenta', 'castka_kategorie')


@admin.register(PlanMonth)
class PlanMonthAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'castka_celkem', 'je_aktualni', 'vytvoreno_kdy', 'vytvoril')
    list_filter = ('rok', 'mesic', 'je_aktualni')
    inlines = [PlanStoreInline]


@admin.register(PlanStore)
class PlanStoreAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'podil_procenta', 'castka_prodejna', 'castka_prodej', 'castka_servis', 'zamknuto')
    list_filter = ('plan_mesic__rok', 'plan_mesic__mesic', 'prodejna')
    inlines = [PlanCategoryInline]


@admin.register(PlanCategory)
class PlanCategoryAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'kategorie_kod', 'podil_procenta', 'castka_kategorie')
    list_filter = ('kategorie_kod',)
