from django.urls import path

from . import views

urlpatterns = [
    path('status/', views.finance_status, name='finance-status'),
    path('kategorie/', views.naklad_kategorie_list, name='finance-kategorie'),
    path('naklady/nezarazene/', views.naklady_nezarazene, name='finance-naklady-nezarazene'),
    path('naklady/prehled/', views.naklady_prehled, name='finance-naklady-prehled'),
    path('naklady/ceka-na-fakturu/', views.naklady_ceka_na_fakturu, name='finance-naklady-ceka-fakturu'),
    path('naklady/analytika/', views.naklady_analytika, name='finance-naklady-analytika'),
    path('naklady/manual/', views.naklad_manual_create, name='finance-naklad-manual'),
    path('naklady/<int:polozka_id>/', views.naklad_update, name='finance-naklad-update'),
    path('pravidla/', views.pravidla_list_create, name='finance-pravidla'),
    path('pravidla/<int:pravidlo_id>/', views.pravidlo_delete, name='finance-pravidlo-delete'),
    path('doklady/', views.doklady_list, name='finance-doklady-list'),
    path('doklady/ke-kontrole/', views.doklady_ke_kontrole, name='finance-doklady-ke-kontrole'),
    path('doklady/upload/', views.doklad_upload, name='finance-doklad-upload'),
    path('doklady/<int:doklad_id>/', views.doklad_update, name='finance-doklad-update'),
    path('doklady/<int:doklad_id>/schvalit/', views.doklad_schvalit, name='finance-doklad-schvalit'),
    path('doklady/<int:doklad_id>/zamitnout/', views.doklad_zamitnout, name='finance-doklad-zamitnout'),
    path('doklady/<int:doklad_id>/reprocess-ocr/', views.doklad_reprocess_ocr, name='finance-doklad-reprocess'),
]
