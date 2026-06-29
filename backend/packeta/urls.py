from django.urls import path

from . import views

urlpatterns = [
    path('status/', views.packeta_status, name='packeta-status'),
    path('import-csv/', views.packeta_import_csv, name='packeta-import-csv'),
    path('fetch/', views.packeta_fetch_all, name='packeta-fetch'),
]
