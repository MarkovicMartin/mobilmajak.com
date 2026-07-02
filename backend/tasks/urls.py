from django.urls import path

from . import slack_views, views

urlpatterns = [
    # Slack – s lomítkem i bez (portal často vloží URL bez /)
    path('slack/events/', slack_views.slack_events, name='tasks_slack_events'),
    path('slack/events', slack_views.slack_events),
    path('slack/interactions/', slack_views.slack_interactions, name='tasks_slack_interactions'),
    path('slack/interactions', slack_views.slack_interactions),
    path('slack/commands/ukol/', slack_views.slack_slash_ukol, name='tasks_slack_slash_ukol'),
    path('slack/commands/ukol', slack_views.slack_slash_ukol),
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
