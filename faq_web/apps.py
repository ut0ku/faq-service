"""Конфигурация приложения вопросов и ответов."""

from django.apps import AppConfig


class FaqWebConfig(AppConfig):
    """Приложение веб-страниц вопросов и ответов."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "faq_web"
