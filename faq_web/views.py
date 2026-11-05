"""Представления сервиса вопросов и ответов."""

from datetime import date

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from models import Answer as DomainAnswer
from models import Question as DomainQuestion
from models import Section as DomainSection
from models import User as DomainUser
from questions import create_answer, create_question

from .models import Answer, Question, Section, User


def _questions_with_answers():
    return Question.objects.select_related(
        "section",
        "author",
    ).prefetch_related(
        Prefetch(
            "answers",
            queryset=Answer.objects.select_related("author").order_by("pk"),
        )
    )


def question_list(request):
    """Показать вопросы с фильтрами, сортировкой и постраничным выводом."""
    question_date = request.GET.get("date", "").strip()
    section_name = request.GET.get("section", "").strip()
    author_name = request.GET.get("author", "").strip()
    search_query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "date").strip()
    sort_fields = {
        "date": "-created_at",
        "title": "title",
        "section": "section__name",
        "author": "author__name",
    }
    if sort not in sort_fields:
        sort = "date"

    questions = _questions_with_answers().annotate(
        section_name=F("section__name"),
        author_name=F("author__name"),
        answer_count=Count("answers", distinct=True),
    )
    error = ""
    if question_date:
        try:
            selected_date = date.fromisoformat(question_date)
        except ValueError:
            error = "Укажите корректную дату."
            questions = questions.none()
        else:
            questions = questions.filter(created_at=selected_date)
    if section_name:
        questions = questions.filter(section__name=section_name)
    if author_name:
        questions = questions.filter(author__name__icontains=author_name)
    if search_query:
        questions = questions.filter(
            Q(title__icontains=search_query)
            | Q(text__icontains=search_query)
            | Q(section__name__icontains=search_query)
            | Q(author__name__icontains=search_query)
            | Q(answers__text__icontains=search_query)
        ).distinct()

    questions = questions.order_by(sort_fields[sort], "pk")
    page_obj = Paginator(questions, 5).get_page(request.GET.get("page"))
    return render(
        request,
        "faq_web/question_list.html",
        {
            "questions": page_obj,
            "page_obj": page_obj,
            "question_date": question_date,
            "selected_section": section_name,
            "author_name": author_name,
            "search_query": search_query,
            "sort": sort,
            "sections": Section.objects.filter(
                is_active=True
            ).order_by("name"),
            "error": error,
        },
    )


def section_list(request):
    """Показать активные разделы или вопросы выбранного раздела."""
    section_name = request.GET.get("section", "").strip()
    if section_name:
        selected_section = get_object_or_404(Section, name=section_name)
        section_questions = _questions_with_answers().filter(
            section=selected_section
        ).annotate(answer_count=Count("answers", distinct=True))
        sections = []
    else:
        selected_section = None
        section_questions = []
        sections = Section.objects.filter(is_active=True).annotate(
            question_count=Count("questions", distinct=True)
        ).order_by("name")
    return render(
        request,
        "faq_web/section_list.html",
        {
            "sections": sections,
            "selected_section": selected_section,
            "questions": section_questions,
        },
    )


@require_http_methods(["GET", "POST"])
def question_create(request):
    """Показать форму и сохранить новый вопрос через ORM."""
    active_sections = Section.objects.filter(is_active=True).order_by("name")
    error = ""
    if request.method == "POST":
        author_name = request.POST.get("author", "").strip()
        title = request.POST.get("title", "")
        text = request.POST.get("text", "")
        selected_section = active_sections.filter(
            name=request.POST.get("section", "")
        ).first()
        domain_section = (
            DomainSection(selected_section.name, selected_section.is_active)
            if selected_section is not None
            else None
        )

        if not author_name:
            error = "Укажите имя автора."
        elif domain_section is None:
            error = "Выберите доступный раздел."
        else:
            try:
                domain_question = create_question(
                    [],
                    domain_section,
                    role="user",
                    is_authenticated=True,
                    title=title,
                    text=text,
                    author=author_name,
                )
            except (PermissionError, ValueError) as exception:
                error = str(exception)
            else:
                with transaction.atomic():
                    author, _ = User.objects.get_or_create(name=author_name)
                    question = Question.objects.create(
                        section=selected_section,
                        author=author,
                        title=domain_question.title,
                        text=domain_question.text,
                        created_at=domain_question.created_at,
                        status=domain_question.status,
                    )
                return redirect("faq:detail", question_id=question.pk)

    return render(
        request,
        "faq_web/question_create.html",
        {
            "sections": active_sections,
            "form_data": request.POST if request.method == "POST" else {},
            "error": error,
        },
        status=400 if error else 200,
    )


@require_http_methods(["GET", "POST"])
def question_detail(request, question_id: int):
    """Показать вопрос и ответы, при POST сохранить ответ через ORM."""
    question = get_object_or_404(
        _questions_with_answers(),
        pk=question_id,
    )
    answers = list(question.answers.all())
    error = ""
    if request.method == "POST":
        author_name = request.POST.get("author", "").strip()
        text = request.POST.get("text", "")
        if not author_name:
            error = "Укажите имя автора."
        else:
            domain_question = DomainQuestion(
                id=question.pk,
                section=question.section.name,
                title=question.title,
                text=question.text,
                author=DomainUser(question.author.name),
                created_at=question.created_at,
                status=question.status,
                answers=[
                    DomainAnswer(
                        DomainUser(answer.author.name),
                        answer.text,
                        answer.created_at,
                    )
                    for answer in answers
                ],
            )
            try:
                domain_answer = create_answer(
                    [domain_question],
                    role="user",
                    is_authenticated=True,
                    question_id=question.pk,
                    text=text,
                    author=author_name,
                )
            except (LookupError, PermissionError, ValueError) as exception:
                error = str(exception)
            else:
                with transaction.atomic():
                    author, _ = User.objects.get_or_create(name=author_name)
                    Answer.objects.create(
                        question=question,
                        author=author,
                        text=domain_answer.text,
                        created_at=domain_answer.created_at,
                    )
                return redirect("faq:detail", question_id=question.pk)

    return render(
        request,
        "faq_web/question_detail.html",
        {
            "question": question,
            "answers": answers,
            "form_data": request.POST if request.method == "POST" else {},
            "error": error,
        },
        status=400 if error else 200,
    )


def statistics(request):
    """Показать агрегированную статистику вопросов и ответов."""
    sections = Section.objects.annotate(
        questions_count=Count("questions", distinct=True),
        answers_count=Count("questions__answers", distinct=True),
    ).order_by("-questions_count", "name").values(
        "name",
        "questions_count",
        "answers_count",
    )
    question_totals = Question.objects.aggregate(
        questions_count=Count("pk"),
        closed_questions=Count("pk", filter=Q(status=Question.Status.CLOSED)),
    )
    question_totals["open_questions"] = Question.objects.exclude(
        status=Question.Status.CLOSED
    ).count()
    answer_totals = Answer.objects.aggregate(answers_count=Count("pk"))
    totals = {**question_totals, **answer_totals}
    return render(
        request,
        "faq_web/statistics.html",
        {"sections": sections, "totals": totals},
    )
