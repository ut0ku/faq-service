"""Маршруты главной страницы."""

from django.urls import path

from . import views

# пространство имен
app_name = "homepage"

urlpatterns = [
    path("", views.index, name="index"),
]
