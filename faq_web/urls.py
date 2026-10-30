"""Маршруты страниц вопросов и ответов."""

from django.urls import path

from . import views

# пространство имен
app_name = "faq"

urlpatterns = [
    path("", views.question_list, name="list"),
    path("new/", views.question_create, name="create"),
    path("sections/", views.section_list, name="sections"),
    path("statistics/", views.statistics, name="statistics"),
    # маршрут для отображения деталей вопроса (с конвертером)
    path("<int:question_id>/", views.question_detail, name="detail"),
]
