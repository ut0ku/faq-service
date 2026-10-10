"""Представления для списка вопросов и их подробных страниц."""

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from questions import (
    create_answer,
    create_question,
    find_question,
    sort_questions,
)
from storage import load_data, save_data


def _data_path():
    """Вернуть путь к общему JSON-хранилищу проекта ПР3."""
    return settings.BASE_DIR / "data" / "faq.json"


def question_list(request):
    """Показать вопросы FAQ в обратном хронологическом порядке."""
    _, questions = load_data(_data_path())
    return render(
        request,
        "faq_web/question_list.html",
        {"questions": sort_questions(questions)},
    )


@require_http_methods(["GET", "POST"])
def question_create(request):
    """Показать форму и сохранить новый вопрос в JSON."""
    sections, questions = load_data(_data_path())
    active_sections = [section for section in sections if section.is_active]
    form_data = request.POST if request.method == "POST" else {}
    error = ""

    if request.method == "POST":
        author = form_data.get("author", "").strip()
        title = form_data.get("title", "")
        text = form_data.get("text", "")
        section_name = form_data.get("section", "")
        section = next(
            (
                item
                for item in active_sections
                if item.name == section_name
            ),
            None,
        )
        if not author:
            error = "Укажите имя автора."
        elif section is None:
            error = "Выберите доступный раздел."
        else:
            try:
                question = create_question(
                    questions,
                    section,
                    role="user",
                    is_authenticated=True,
                    title=title,
                    text=text,
                    author=author,
                )
                save_data(_data_path(), sections, questions)
            except (PermissionError, ValueError) as exception:
                error = str(exception)
            else:
                return redirect("faq:detail", question_id=question.id)

    return render(
        request,
        "faq_web/question_create.html",
        {
            "sections": active_sections,
            "form_data": form_data,
            "error": error,
        },
        status=400 if error else 200,
    )


@require_http_methods(["GET", "POST"])
def question_detail(request, question_id: int):
    """Показать вопрос и ответы, при POST добавить ответ."""
    sections, questions = load_data(_data_path())
    try:
        question = find_question(question_id, questions)
    except LookupError as error:
        raise Http404("Вопрос не найден") from error

    form_data = request.POST if request.method == "POST" else {}
    error = ""
    if request.method == "POST":
        author = form_data.get("author", "").strip()
        text = form_data.get("text", "")
        if not author:
            error = "Укажите имя автора."
        else:
            try:
                create_answer(
                    questions,
                    role="user",
                    is_authenticated=True,
                    question_id=question_id,
                    text=text,
                    author=author,
                )
                save_data(_data_path(), sections, questions)
            except (LookupError, PermissionError, ValueError) as exception:
                error = str(exception)
            else:
                return redirect("faq:detail", question_id=question_id)

    return render(
        request,
        "faq_web/question_detail.html",
        {
            "question": question,
            "form_data": form_data,
            "error": error,
        },
        status=400 if error else 200,
    )
