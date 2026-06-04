from django.urls import path
from . import views

urlpatterns = [
    path('', views.plany_prehled, name='plany-prehled'),
    path('forecast/', views.plan_forecast_nahled, name='plan-forecast-nahled'),
    path('forecast/create-year/', views.plan_forecast_create_year, name='plan-forecast-create-year'),
    path('muj-plan/', views.muj_plan, name='muj-plan'),
    path('<int:rok>/<int:mesic>/', views.plan_mesic, name='plan-mesic'),
    path('<int:rok>/<int:mesic>/audit-zbytek/', views.audit_zbytek, name='plan-audit-zbytek'),
    path('<int:rok>/<int:mesic>/plneni/', views.plan_plneni, name='plan-plneni'),
    path('<int:rok>/<int:mesic>/plneni-prodejci/', views.plan_plneni_prodejci, name='plan-plneni-prodejci'),
    path('<int:rok>/<int:mesic>/plneni-polozky/', views.plan_plneni_polozky, name='plan-plneni-polozky'),
    path('<int:rok>/<int:mesic>/historie-nahled/', views.plan_historie_nahled, name='plan-historie-nahled'),
    path('<int:rok>/<int:mesic>/historie-3m-nahled/', views.plan_historie_3m_nahled, name='plan-historie-3m-nahled'),
    path('<int:rok>/<int:mesic>/historie-auto-nahled/', views.plan_historie_auto_nahled, name='plan-historie-auto-nahled'),
    path('<int:rok>/<int:mesic>/ulozit/', views.plan_ulozit, name='plan-ulozit'),
    path('<int:rok>/<int:mesic>/prepocet/', views.plan_prepocet, name='plan-prepocet'),
    path('verze/<int:verze_id>/', views.plan_verze_detail, name='plan-verze-detail'),
    path('verze/<int:verze_id>/set-aktualni/', views.plan_set_aktualni, name='plan-set-aktualni'),
    path('prodejna/<int:plan_prodejna_id>/prodejci/', views.plan_prodejci, name='plan-prodejci'),
    path('prodejna/<int:plan_prodejna_id>/prodejci/ulozit/', views.plan_prodejci_ulozit, name='plan-prodejci-ulozit'),
    path('prodejna/<int:plan_prodejna_id>/prodejci/auto/', views.plan_prodejci_auto, name='plan-prodejci-auto'),
]
