"""Маршруты страниц вопросов и ответов."""

from django.urls import path

from . import views

app_name = "faq"

urlpatterns = [
    path("", views.question_list, name="list"),
    path("new/", views.question_create, name="create"),
    path("<int:question_id>/", views.question_detail, name="detail"),
]
