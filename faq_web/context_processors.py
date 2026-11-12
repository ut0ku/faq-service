"""Общие данные для шаблонов FAQ."""

from .models import Question


def faq_context(request):
    """Передать общее название сервиса и число открытых вопросов."""
    return {
        "site_name": "FAQ Service",
        "open_questions_count": Question.objects.open().count(),
    }
