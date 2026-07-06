from django.urls import path

from . import views

urlpatterns = [
    path('status/', views.finance_status, name='finance-status'),
    path('kategorie/', views.naklad_kategorie_list, name='finance-kategorie'),
    path('naklady/nezarazene/', views.naklady_nezarazene, name='finance-naklady-nezarazene'),
    path('naklady/manual/', views.naklad_manual_create, name='finance-naklad-manual'),
    path('naklady/<int:polozka_id>/', views.naklad_update, name='finance-naklad-update'),
    path('pravidla/', views.pravidla_list_create, name='finance-pravidla'),
    path('pravidla/<int:pravidlo_id>/', views.pravidlo_delete, name='finance-pravidlo-delete'),
    path('doklady/', views.doklady_list_stub, name='finance-doklady-list'),
    path('doklady/upload/', views.doklad_upload_stub, name='finance-doklad-upload'),
]
