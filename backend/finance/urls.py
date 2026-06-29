from django.urls import path

from . import views

urlpatterns = [
    path('status/', views.finance_status, name='finance-status'),
    path('kategorie/', views.naklad_kategorie_list, name='finance-kategorie'),
    path('naklady/nezarazene/', views.naklady_nezarazene, name='finance-naklady-nezarazene'),
    path('naklady/manual/', views.naklad_manual_create, name='finance-naklad-manual'),
    path('naklady/<int:polozka_id>/', views.naklad_update, name='finance-naklad-update'),
    path('pravidla/', views.pravidlo_create, name='finance-pravidlo-create'),
]
