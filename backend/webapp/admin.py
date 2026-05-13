from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

# Customizace hlavního admin site
class WebAppAdminSite(AdminSite):
    site_header = "Web Majak - Administrace"
    site_title = "Web Majak Admin"
    index_title = "Správa systému Web Majak"
    
    def each_context(self, request):
        """
        Přidává extra kontext do admin šablon
        """
        context = super().each_context(request)
        context.update({
            'available_apps_custom': self._build_app_dict(request),
        })
        return context
    
    def _build_app_dict(self, request):
        """
        Organizuje aplikace do logických skupin
        """
        app_dict = self._build_app_dict_original(request)
        
        # Definujeme pořadí a skupiny aplikací
        app_order = {
            'stores': {'order': 1, 'verbose_name': 'Správa prodejen'},
            'users': {'order': 2, 'verbose_name': 'Správa uživatelů'},
            'news': {'order': 3, 'verbose_name': 'Správa kategorií'},
            'shifts': {'order': 4, 'verbose_name': 'Nastavení modulů'},
            'web_pristupy': {'order': 5, 'verbose_name': 'Systémové nastavení'},
            'analytics': {'order': 6, 'verbose_name': 'Analytics'},
        }
        
        # Seřadíme aplikace podle definovaného pořadí
        ordered_apps = []
        for app_label, config in sorted(app_order.items(), key=lambda x: x[1]['order']):
            if app_label in app_dict:
                app = app_dict[app_label]
                # Můžeme přepsat název aplikace
                if 'verbose_name' in config:
                    app['name'] = config['verbose_name']
                ordered_apps.append(app)
        
        # Přidáme zbývající aplikace, které nejsou v app_order
        for app_label, app in app_dict.items():
            if app_label not in app_order:
                ordered_apps.append(app)
        
        return ordered_apps
    
    def _build_app_dict_original(self, request):
        """
        Kopie původní metody pro získání app_dict
        """
        from django.contrib.admin.sites import site
        return site._build_app_dict(request)

# Vytvoříme vlastní admin site instanci
admin_site = WebAppAdminSite(name='webmajak_admin')

# Nastavíme výchozí admin site titulky
admin.site.site_header = "Web Majak - Administrace"
admin.site.site_title = "Web Majak Admin"
admin.site.index_title = "Správa systému Web Majak" 