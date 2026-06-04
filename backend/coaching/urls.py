from django.urls import path

from coaching import views

urlpatterns = [
    path('filters/options/', views.filters_options, name='coaching-filters'),
    path('roster/', views.roster_view, name='coaching-roster'),
    path('sellers/<int:user_id>/profile/', views.seller_profile, name='coaching-seller-profile'),
    path('sellers/<int:user_id>/timeline/', views.seller_timeline, name='coaching-seller-timeline'),
    path('sellers/<int:user_id>/tasks/', views.seller_tasks, name='coaching-seller-tasks'),
    path('sellers/compare/', views.sellers_compare, name='coaching-sellers-compare'),
    path('notes/', views.notes_list_create, name='coaching-notes'),
    path('notes/<int:note_id>/', views.note_detail, name='coaching-note-detail'),
    path('goals/', views.goals_list_create, name='coaching-goals'),
    path('goals/<int:goal_id>/', views.goal_detail, name='coaching-goal-detail'),
]
