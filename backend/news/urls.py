from django.urls import path
from . import views

urlpatterns = [
    # Novinky
    path('', views.NovinkaListCreateView.as_view(), name='novinky-list-create'),
    path('<int:pk>/', views.NovinkaDetailView.as_view(), name='novinka-detail'),
    
    # Komentáře
    path('<int:novinka_id>/komentare/', views.KomentarListCreateView.as_view(), name='komentare-list-create'),
    path('komentare/<int:pk>/', views.KomentarDetailView.as_view(), name='komentar-detail'),
    
    # Reakce
    path('reakce/', views.ReakceCreateView.as_view(), name='reakce-create'),
    path('<int:novinka_id>/reakce/', views.odstranit_reakci, name='reakce-delete'),
    
    # Soubory novinek
    path('<int:novinka_id>/soubory/', views.nahrat_soubor_novinky, name='novinka-soubor-upload'),
    path('soubory/<int:soubor_id>/', views.odstranit_soubor_novinky, name='novinka-soubor-delete'),
    
    # Soubory komentářů
    path('komentare/<int:komentar_id>/soubory/', views.nahrat_soubor_komentare, name='komentar-soubor-upload'),
    path('komentare/soubory/<int:soubor_id>/', views.odstranit_soubor_komentare, name='komentar-soubor-delete'),
    
    # Kategorie
    path('kategorie/', views.KategorieListView.as_view(), name='kategorie-list'),
    path('kategorie/vytvorit/', views.KategorieCreateView.as_view(), name='kategorie-create'),
    path('kategorie/<int:pk>/', views.KategorieDetailView.as_view(), name='kategorie-detail'),
] 