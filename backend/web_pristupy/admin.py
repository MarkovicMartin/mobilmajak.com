from django.contrib import admin
from .models import WEB_PRISTUPY_PRODEJNY

@admin.register(WEB_PRISTUPY_PRODEJNY)
class WebPristupyProdejnyAdmin(admin.ModelAdmin):
    """Admin rozhraní pro správu přístupů prodejen"""
    
    list_display = [
        'company_name', 
        'store', 
        'username', 
        'masked_password_display',
        'category', 
        'is_active',
        'last_used',
        'added_by'
    ]
    
    list_filter = [
        'store', 
        'category', 
        'is_active', 
        'added_by',
        'created_at'
    ]
    
    search_fields = [
        'company_name', 
        'website_url', 
        'username', 
        'description',
        'notes'
    ]
    
    readonly_fields = [
        'created_at', 
        'updated_at',
        'last_used'
    ]
    
    fieldsets = (
        ('Základní informace', {
            'fields': (
                'company_name',
                'website_url',
                'category',
                'store'
            )
        }),
        ('Přihlašovací údaje', {
            'fields': (
                'username',
                'password'
            )
        }),
        ('Doplňující informace', {
            'fields': (
                'description',
                'notes'
            )
        }),
        ('Systémové informace', {
            'fields': (
                'added_by',
                'is_active',
                'last_used',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def masked_password_display(self, obj):
        """Zobrazí zamaskované heslo v admin seznamu"""
        return obj.masked_password
    masked_password_display.short_description = "Heslo"
    
    def get_queryset(self, request):
        """Upravuje queryset pro admin zobrazení"""
        qs = super().get_queryset(request)
        return qs.select_related()  # Pro optimalizaci dotazů
    
    def save_model(self, request, obj, form, change):
        """Přepíše save_model pro automatické nastavení added_by"""
        if not change:  # Pouze při vytváření nového záznamu
            obj.added_by = request.user.username
        super().save_model(request, obj, form, change)
