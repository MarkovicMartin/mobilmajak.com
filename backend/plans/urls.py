from django.urls import path
from . import views

urlpatterns = [
    path('', views.plany_prehled, name='plany-prehled'),
    path('muj-plan/', views.muj_plan, name='muj-plan'),
    path('<int:rok>/<int:mesic>/', views.plan_mesic, name='plan-mesic'),
    path('<int:rok>/<int:mesic>/plneni/', views.plan_plneni, name='plan-plneni'),
    path('<int:rok>/<int:mesic>/plneni-prodejci/', views.plan_plneni_prodejci, name='plan-plneni-prodejci'),
    path('<int:rok>/<int:mesic>/historie-nahled/', views.plan_historie_nahled, name='plan-historie-nahled'),
    path('<int:rok>/<int:mesic>/ulozit/', views.plan_ulozit, name='plan-ulozit'),
    path('<int:rok>/<int:mesic>/prepocet/', views.plan_prepocet, name='plan-prepocet'),
    path('verze/<int:verze_id>/', views.plan_verze_detail, name='plan-verze-detail'),
    path('verze/<int:verze_id>/set-aktualni/', views.plan_set_aktualni, name='plan-set-aktualni'),
    path('prodejna/<int:plan_prodejna_id>/prodejci/', views.plan_prodejci, name='plan-prodejci'),
    path('prodejna/<int:plan_prodejna_id>/prodejci/ulozit/', views.plan_prodejci_ulozit, name='plan-prodejci-ulozit'),
]
