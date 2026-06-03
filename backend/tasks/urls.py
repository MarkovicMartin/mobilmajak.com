from django.urls import path
from . import views

urlpatterns = [
    path('', views.tasks_list_create, name='tasks_list_create'),
    path('unread-summary/', views.tasks_unread_summary, name='tasks_unread_summary'),
    path('<int:task_id>/', views.task_detail, name='task_detail'),
]


