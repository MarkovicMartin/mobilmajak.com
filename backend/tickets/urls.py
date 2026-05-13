from django.urls import path
from . import views

urlpatterns = [
    path('unread-summary/', views.tickets_unread_summary, name='tickets_unread_summary'),
    path('', views.tickets_list_create, name='tickets_list_create'),
    path('<int:ticket_id>/mark-read/', views.ticket_mark_read, name='ticket_mark_read'),
    path(
        '<int:ticket_id>/comments/<int:comment_id>/',
        views.ticket_comment_modify,
        name='ticket_comment_modify',
    ),
    path('<int:ticket_id>/comments/', views.ticket_add_comment, name='ticket_add_comment'),
    path('<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
]
