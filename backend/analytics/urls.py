from django.urls import path
from . import views
# from . import views_apify  # Commented out as file may not exist

app_name = 'analytics'

urlpatterns = [
    # NOVÉ APIFY ENDPOINTY (DOPORUČENÉ) - COMMENTED OUT AS views_apify DOESN'T EXIST
    # ===================================
    
    # # API endpoint pro načítání dat z Apify tabulek
    # path('apify/data/', views_apify.ApifyDataView.as_view(), name='apify_data'),
    
    # # API endpoint pro data podle konkrétního data z Apify tabulek
    # path('apify/data/by-date/', views_apify.get_apify_data_by_date, name='apify_data_by_date'),
    
    # # Apify endpointy pro analytiku prodejce
    # path('apify/salesperson/today/', views_apify.get_salesperson_today_data_apify, name='apify_salesperson_today'),
    # path('apify/salesperson/monthly/', views_apify.get_salesperson_monthly_data_apify, name='apify_salesperson_monthly'),
    
    # # Apify endpointy pro body prodejce
    # path('apify/salesperson/points/today/', views_apify.get_salesperson_points_today_apify, name='apify_salesperson_points_today'),
    # path('apify/salesperson/points/monthly/', views_apify.get_salesperson_points_monthly_apify, name='apify_salesperson_points_monthly'),
    
    # # Apify endpointy pro žebříčky
    # path('apify/leaderboard/points/', views_apify.get_leaderboard_monthly_points_apify, name='apify_leaderboard_monthly_points'),
    # path('apify/leaderboard/average-items/', views_apify.get_leaderboard_average_items_apify, name='apify_leaderboard_average_items'),
    
    # # Apify endpoint pro interaktivní grafy
    # path('apify/charts-data/', views_apify.get_charts_data_apify, name='apify_charts_data'),
    
    # # Endpoint pro informace o posledním Apify importu
    # path('apify/backup-info/', views_apify.get_apify_backup_info, name='apify_backup_info'),
    
    
    # WEB_PRODEJE ENDPOINTY (NEJNOVĚJŠÍ - PŘÍMO Z PRODEJNÍ TABULKY)
    # =============================================================
    
    # API endpoint pro modul "Prodejny - Položky" z tabulky WEB_PRODEJE
    path('web-prodeje/polozky/', views.web_prodeje_polozky_view, name='web_prodeje_polozky'),
    # Leaderboardy z WEB_PRODEJE_ALL
    path('web-prodeje/leaderboard/points/', views.web_prodeje_leaderboard_points, name='web_prodeje_leaderboard_points'),
    path('web-prodeje/leaderboard/average-items/', views.web_prodeje_leaderboard_average_items, name='web_prodeje_leaderboard_average_items'),

    # Profil prodejce (Můj profil) – čteno přímo z WEB_PRODEJE_ALL
    path('web-prodeje/salesperson/today/', views.web_prodeje_salesperson_today, name='web_prodeje_salesperson_today'),
    path('web-prodeje/salesperson/monthly/', views.web_prodeje_salesperson_monthly, name='web_prodeje_salesperson_monthly'),
    path('web-prodeje/salesperson/points/today/', views.web_prodeje_salesperson_points_today, name='web_prodeje_salesperson_points_today'),
    path('web-prodeje/salesperson/points/monthly/', views.web_prodeje_salesperson_points_monthly, name='web_prodeje_salesperson_points_monthly'),
    path('web-prodeje/salesperson/active-dates/', views.web_prodeje_salesperson_active_dates, name='web_prodeje_salesperson_active_dates'),
    
    
    # STARÉ GOOGLE SHEETS ENDPOINTY (DEPRECATED - ZACHOVAT PRO ZPĚTNOU KOMPATIBILITU)
    # =============================================================================
    
    # API endpoint pro načítání dat z Google Sheets (DEPRECATED)
    path('prodejny-data/', views.ProdejnyDataView.as_view(), name='prodejny_data'),
    
    # API endpoint pro uložení dat do databáze (DEPRECATED)
    path('prodejny-data/save/', views.SaveProdejnyDataView.as_view(), name='save_prodejny_data'),
    
    # Debug endpoint pro diagnostiku ukládání (DEPRECATED)
    path('prodejny-data/debug/', views.DebugProdejnyDataView.as_view(), name='debug_prodejny_data'),
    
    # API endpoint pro historická data (DEPRECATED)
    path('prodejny-data/historical/', views.get_historical_data, name='historical_data'),
    
    # API endpoint pro data podle konkrétního data (DEPRECATED)
    path('prodejny-data/by-date/', views.get_data_by_date, name='data_by_date'),
    
    # Nové endpointy pro analytiku prodejce (DEPRECATED)
    path('salesperson/analytics/', views.get_salesperson_analytics, name='salesperson_analytics'),
    path('salesperson/today/', views.get_salesperson_today_data, name='salesperson_today'),
    path('salesperson/monthly/', views.get_salesperson_monthly_data, name='salesperson_monthly'),
    
    # Nové endpointy pro body prodejce (DEPRECATED)
    path('salesperson/points/today/', views.get_salesperson_points_today, name='salesperson_points_today'),
    path('salesperson/points/monthly/', views.get_salesperson_points_monthly, name='salesperson_points_monthly'),
    
    # Nové endpointy pro žebříčky (DEPRECATED)
    path('leaderboard/points/', views.get_leaderboard_monthly_points, name='leaderboard_monthly_points'),
    path('leaderboard/average-items/', views.get_leaderboard_average_items, name='leaderboard_average_items'),
    
    # Nový endpoint pro interaktivní grafy (DEPRECATED)
    path('charts-data/', views.get_charts_data, name='charts_data'),
    
    # Endpoint pro informace o posledním automatickém zálohování (DEPRECATED)
    path('backup-info/', views.get_last_backup_info, name='backup_info'),
    
    # CELKOVÁ ČÍSLA - Nové endpointy pro analýzu WEB_PRODEJE
    path('celkova-cisla/', views.celkova_cisla_view, name='celkova_cisla'),
    path('celkova-cisla/trendy/', views.celkova_cisla_trendy_view, name='celkova_cisla_trendy'),
    path('celkova-cisla/categories-timeseries/', views.celkova_categories_timeseries_view, name='celkova_categories_timeseries'),
    path('celkova-cisla/prodejna-detail/', views.celkova_prodejna_detail_view, name='celkova_prodejna_detail'),
    path('celkova-cisla/servis-detail/', views.celkova_servis_detail_view, name='celkova_servis_detail'),
    path('celkova-cisla/channel-items/', views.celkova_channel_items_view, name='celkova_channel_items'),
    path('celkova-cisla/zasilkovna-detail/', views.zasilkovna_detail_view, name='zasilkovna_detail'),

    # ZÁKAZNÍCI - Počet unikátních zákazníků z WEB_PRODEJE_ALL
    path('zakaznici/', views.zakaznici_view, name='zakaznici'),
    path('zakaznici/timeseries/', views.zakaznici_timeseries_view, name='zakaznici_timeseries'),
    
    # NOVÝ MODUL - TRAFFIC ANALYTICS
    path('prodejny-zakaznici/traffic/', views.StoreTrafficView.as_view(), name='store_traffic'),
    
    # E-SHOP - Nové endpointy pro analýzu e-shop dat z WEB_PRODEJE
    path('eshop/', views.eshop_data_view, name='eshop_data'),
    path('eshop/categories-analytics/', views.eshop_categories_analytics_view, name='eshop_categories_analytics'),
    path('eshop/categories-timeseries/', views.eshop_categories_timeseries_view, name='eshop_categories_timeseries'),
    path('eshop/channel-detail/', views.eshop_channel_detail_view, name='eshop_channel_detail'),
    path('eshop/channel-items/', views.eshop_channel_items_view, name='eshop_channel_items'),
    
    # SERVIS - Nové endpointy pro analýzu servisních dat z WEB_PRODEJE
    path('servis/', views.servis_data_view, name='servis_data'),
    path('servis/trendy/', views.servis_trendy_view, name='servis_trendy'),
    path('servis/prodejna-detail/', views.servis_prodejna_detail_view, name='servis_prodejna_detail'),
    path('servis/prodejna-items/', views.servis_prodejna_items_view, name='servis_prodejna_items'),
    path('servis/technik-detail/', views.servis_technik_detail_view, name='servis_technik_detail'),
    path('servis/technik-items/', views.servis_technik_items_view, name='servis_technik_items'),
    path('servis/typ-items/', views.servis_typ_items_view, name='servis_typ_items'),
    path('servis/debug-rozdil/', views.debug_servis_rozdil_view, name='debug_servis_rozdil'),
    
    # PRODEJNÍ ANALYTIKA - Nové endpointy pro pokročilé analýzy z WEB_PRODEJE
    path('prodejni-analytika/', views.prodejni_analytika_view, name='prodejni_analytika'),
    # Telefony + příslušenství ≥ 100 Kč na doklad
    path('prodejni-analytika/phones-accessories/', views.phones_accessories_view, name='phones_accessories'),
    path('prodejni-analytika/phones-accessories/receipt-items/', views.phones_accessories_receipt_items_view, name='phones_accessories_receipt_items'),
    path('prodejni-analytika/phones-accessories/by-salesperson/', views.phones_accessories_by_salesperson_view, name='phones_accessories_by_salesperson'),
    path('prodejni-analytika/phones-accessories/salesperson-receipts/', views.phones_accessories_salesperson_receipts_view, name='phones_accessories_salesperson_receipts'),
    
    # GRAFY Z WEB_PRODEJE - Nové endpointy pro interaktivní grafy
    path('web-prodeje-charts-data/', views.get_web_prodeje_charts_data, name='web_prodeje_charts_data'),
    
    # WEBHOOK ENDPOINTY - Pro externí integrace (N8N, atd.)
    path('webhook/monthly-stats/', views.webhook_monthly_stats, name='webhook_monthly_stats'),

] 