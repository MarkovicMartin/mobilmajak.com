from django.urls import path
from . import views
from . import payroll_views
from . import camera_views

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
    path('vacation-balance/', views.vacation_balance, name='vacation_balance'),
    path('vacation-overview/', views.vacation_overview, name='vacation_overview'),
    
    # Export pro účetní
    path('export/', views.export_smeny, name='export_smeny'),

    # Payroll (ADMIN)
    path('payroll/', payroll_views.payroll_preview, name='payroll_preview'),
    path('payroll/discounted-services/', payroll_views.payroll_discounted_services, name='payroll_discounted_services'),
    path('payroll/dobropisy/', payroll_views.payroll_dobropisy, name='payroll_dobropisy'),
    path('payroll/odmena/', payroll_views.payroll_odmena, name='payroll_odmena'),
    path('payroll/penalizace/', payroll_views.payroll_penalizace, name='payroll_penalizace'),

    # Docházka log (ADMIN) + stav pro zaměstnance
    path('attendance/log/', payroll_views.attendance_log, name='attendance_log'),
    path('attendance/open/', payroll_views.attendance_open, name='attendance_open'),
    path('attendance/my-status/', payroll_views.attendance_my_status, name='attendance_my_status'),
    path('attendance/absent-stores/', payroll_views.attendance_absent_stores, name='attendance_absent_stores'),
    path('attendance/today-board/', payroll_views.attendance_today_board, name='attendance_today_board'),
    path('camera-events/', camera_views.camera_motion_event, name='camera_motion_event'),
    path(
        'camera-events/hikvision/<int:prodejna_id>/<str:token>/',
        camera_views.camera_hikvision_webhook,
        name='camera_hikvision_webhook',
    ),
] 