"""Представления сервиса вопросов и ответов."""

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST

from models import Answer as DomainAnswer
from models import Question as DomainQuestion
from models import Section as DomainSection
from models import User as DomainUser
from questions import create_answer, create_question

from .forms import (
    QuestionCreateForm,
    QuestionFilterForm,
    QuestionUpdateForm,
)
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
    filter_data = request.GET.copy()
    filter_data.setdefault("sort", "date")
    filter_form = QuestionFilterForm(filter_data)
    filters_are_valid = filter_form.is_valid()
    filters = filter_form.cleaned_data if filters_are_valid else {}
    sort = filters.get("sort") or "date"
    sort_fields = {
        "date": "-created_at",
        "title": "title",
        "section": "section__name",
        "author": "author__name",
    }

    questions = _questions_with_answers().annotate(
        section_name=F("section__name"),
        author_name=F("author__name"),
        answer_count=Count("answers", distinct=True),
    )
    if not filters_are_valid:
        questions = questions.none()
    else:
        question_date = filters.get("date")
        section = filters.get("section")
        author_name = filters.get("author", "")
        search_query = filters.get("q", "")
        if question_date:
            questions = questions.filter(created_at=question_date)
        if section:
            questions = questions.filter(section=section)
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

    questions = questions.order_by(sort_fields.get(sort, "-created_at"), "pk")
    page_obj = Paginator(questions, 5).get_page(request.GET.get("page"))
    return render(
        request,
        "faq_web/question_list.html",
        {
            "questions": page_obj,
            "page_obj": page_obj,
            "filter_form": filter_form,
            "sort": sort,
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
    if request.method == "POST":
        form = QuestionCreateForm(request.POST, request.FILES)
        if form.is_valid():
            author_name = form.cleaned_data["author"]
            selected_section = form.cleaned_data["section"]
            domain_section = DomainSection(
                selected_section.name,
                selected_section.is_active,
            )
            try:
                domain_question = create_question(
                    [],
                    domain_section,
                    role="user",
                    is_authenticated=True,
                    title=form.cleaned_data["title"],
                    text=form.cleaned_data["text"],
                    author=author_name,
                )
            except (PermissionError, ValueError) as exception:
                form.add_error(None, str(exception))
            else:
                with transaction.atomic():
                    author, _ = User.objects.get_or_create(name=author_name)
                    question = form.save(commit=False)
                    question.author = author
                    question.created_at = domain_question.created_at
                    question.status = domain_question.status
                    question.save()
                return redirect("faq:detail", slug=question.slug)
    else:
        form = QuestionCreateForm()
    return render(
        request,
        "faq_web/question_create.html",
        {"form": form},
        status=400 if request.method == "POST" and form.errors else 200,
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def question_update(request, slug: str):
    """Allow staff to edit a question without changing its author or status."""
    question = get_object_or_404(Question, slug=slug)
    if request.method == "POST":
        form = QuestionUpdateForm(
            request.POST,
            request.FILES,
            instance=question,
        )
        if form.is_valid():
            form.save()
            return redirect("faq:detail", slug=question.slug)
    else:
        form = QuestionUpdateForm(instance=question)

    return render(
        request,
        "faq_web/question_edit.html",
        {"form": form, "question": question},
        status=400 if request.method == "POST" and form.errors else 200,
    )


@staff_member_required
@require_POST
def question_close(request, slug: str):
    """Close an open question through a staff-only POST action."""
    question = get_object_or_404(
        Question.objects.open(),
        slug=slug,
    )
    question.status = Question.Status.CLOSED
    question.save(update_fields=["status"])
    return redirect("faq:detail", slug=question.slug)


@require_http_methods(["GET", "POST"])
def question_detail(request, slug: str):
    """Показать вопрос и ответы, при POST сохранить ответ через ORM."""
    question = get_object_or_404(
        _questions_with_answers(),
        slug=slug,
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
                return redirect("faq:detail", slug=question.slug)

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
    question_totals["open_questions"] = Question.objects.open().count()
    answer_totals = Answer.objects.aggregate(answers_count=Count("pk"))
    totals = {**question_totals, **answer_totals}
    return render(
        request,
        "faq_web/statistics.html",
        {"sections": sections, "totals": totals},
    )
