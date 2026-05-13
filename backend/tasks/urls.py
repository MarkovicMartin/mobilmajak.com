from django.urls import path
from . import views

urlpatterns = [
    path('', views.tasks_list_create, name='tasks_list_create'),
    path('<int:task_id>/', views.task_detail, name='task_detail'),
]


