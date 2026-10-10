"""Представления главной страницы и ошибки 404."""

from django.conf import settings
from django.shortcuts import render

from storage import load_data


def index(request):
    """Показать главную страницу с краткой информацией о FAQ."""
    sections, questions = load_data(settings.BASE_DIR / "data" / "faq.json")
    context = {
        "section_count": len(sections),
        "question_count": len(questions),
    }
    return render(request, "homepage/index.html", context)


def page_not_found(request, exception):
    """Показать общую страницу ошибки 404."""
    return render(request, "404.html", status=404)
