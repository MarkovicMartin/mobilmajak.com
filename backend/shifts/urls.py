from django.urls import path
from . import views

urlpatterns = [
    # Počet směn prodejce na prodejně v měsíci (typ=prace)
    path('count/', views.smeny_count, name='smeny_count'),
    # Seznam a vytvoření směn
    path('', views.smeny_list, name='smeny_list'),
    
    # Hromadné vytvoření směn
    path('bulk-create/', views.smeny_bulk_create, name='smeny_bulk_create'),
    
    # Detail směny (úprava, mazání)
    path('<int:smena_id>/', views.smena_detail, name='smena_detail'),
    
    # Kalendářní data
    path('calendar/', views.kalendar_data, name='kalendar_data'),
    
    # Docházka (check-in/out/pauza)
    path('attendance/', views.dochazka_akce, name='dochazka_akce'),
    
    # Přehled hodin pro uživatele
    path('overview/', views.smeny_prehled, name='smeny_prehled'),
    
    # Export pro účetní
    path('export/', views.export_smeny, name='export_smeny'),
] 