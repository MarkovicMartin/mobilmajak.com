from django.urls import path

from . import views

urlpatterns = [
    path("search", views.search_view, name="vallora-search"),
    path("quote", views.quote_view, name="vallora-quote"),
]
