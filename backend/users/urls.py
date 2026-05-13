from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Autentizace
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('current/', views.current_user_view, name='current_user'),
    path('csrf/', views.csrf_token_view, name='csrf_token'),
    
    # Správa uživatelů (pouze pro adminy)
    path('list/', views.users_list_view, name='users_list'),
    path('create/', views.create_user_view, name='create_user'),
    path('update/<int:user_id>/', views.update_user_view, name='update_user'),
    path('delete/<int:user_id>/', views.delete_user_view, name='delete_user'),
    
    # Můj profil
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile_view, name='update_profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('profile/image/', views.profile_image_view, name='profile_image'),
    path('profile/image/upload/', views.upload_profile_image_view, name='upload_profile_image'),
    path('profile/image/delete/', views.delete_profile_image_view, name='delete_profile_image'),
] 