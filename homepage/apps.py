"""Конфигурация приложения главной страницы."""

from django.apps import AppConfig


class HomepageConfig(AppConfig):
    """Приложение главной страницы FAQ Service."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "homepage"
