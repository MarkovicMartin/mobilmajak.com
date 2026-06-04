from django.urls import path

from . import views

urlpatterns = [
    path('', views.tasks_list_create, name='tasks_list_create'),
    path('calendar/', views.tasks_calendar, name='tasks_calendar'),
    path('notifications-summary/', views.tasks_notifications_summary, name='tasks_notifications_summary'),
    path('unread-summary/', views.tasks_unread_summary, name='tasks_unread_summary'),
    path('dashboard-snapshot/', views.tasks_dashboard_snapshot, name='tasks_dashboard_snapshot'),
    path('assignees/', views.tasks_assignees, name='tasks_assignees'),
    path('<int:task_id>/comments/', views.task_comments, name='task_comments'),
    path('<int:task_id>/mark-read/', views.task_mark_read, name='task_mark_read'),
    path('<int:task_id>/', views.task_detail, name='task_detail'),
]
