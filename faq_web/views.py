"""Представления для списка вопросов и их подробных страниц."""

import sqlite3
from contextlib import closing
from datetime import date

from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from db.database import ensure_database, get_connection
from models import Answer, Question, Section, User
from questions import create_answer, create_question


def _connection() -> sqlite3.Connection:
    """Вернуть подключение после подготовки базы при первом запуске."""
    ensure_database()
    return get_connection()


def _load_questions(
    connection: sqlite3.Connection,
    section_name: str | None = None,
    created_at: str | None = None,
) -> list[Question]:
    """Получить вопросы и ответы из SQLite в объектах предметной области."""
    query = """
        SELECT
            q.id, q.title, q.text, q.created_at, q.status,
            s.name AS section_name, u.name AS question_author,
            a.text AS answer_text, a.created_at AS answer_created_at,
            answer_user.name AS answer_author
        FROM questions AS q
        JOIN sections AS s ON s.id = q.section_id
        JOIN users AS u ON u.id = q.user_id
        LEFT JOIN answers AS a ON a.question_id = q.id
        LEFT JOIN users AS answer_user ON answer_user.id = a.user_id
    """
    conditions = []
    parameters = []
    if section_name is not None:
        conditions.append("s.name = ?")
        parameters.append(section_name)
    if created_at is not None:
        conditions.append("q.created_at = ?")
        parameters.append(created_at)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY q.created_at DESC, q.id DESC, a.id"

    questions = {}
    for row in connection.execute(query, parameters):
        question = questions.get(row["id"])
        if question is None:
            question = Question(
                id=row["id"],
                section=row["section_name"],
                title=row["title"],
                text=row["text"],
                author=User(row["question_author"]),
                created_at=date.fromisoformat(row["created_at"]),
                status=row["status"],
            )
            questions[question.id] = question
        if row["answer_text"] is not None:
            question.answers.append(
                Answer(
                    author=User(row["answer_author"]),
                    text=row["answer_text"],
                    created_at=date.fromisoformat(row["answer_created_at"]),
                )
            )
    return list(questions.values())


def _get_or_create_user_id(
    connection: sqlite3.Connection,
    name: str,
) -> int:
    """Найти пользователя по имени или добавить его."""
    row = connection.execute(
        "SELECT id FROM users WHERE name = ?",
        (name,),
    ).fetchone()
    if row is not None:
        return row["id"]
    cursor = connection.execute(
        "INSERT INTO users (name) VALUES (?)",
        (name,),
    )
    return cursor.lastrowid


def question_list(request):
    """Показать вопросы из SQLite; при необходимости отфильтровать по дате."""
    question_date = request.GET.get("date", "").strip()
    with closing(_connection()) as connection:
        questions = _load_questions(
            connection,
            created_at=question_date or None,
        )
    return render(
        request,
        "faq_web/question_list.html",
        {"questions": questions, "question_date": question_date},
    )


def section_list(request):
    """Показать разделы FAQ или вопросы выбранного раздела."""
    section_name = request.GET.get("section", "")
    with closing(_connection()) as connection:
        if section_name:
            row = connection.execute(
                "SELECT name, is_active FROM sections WHERE name = ?",
                (section_name,),
            ).fetchone()
            if row is None:
                raise Http404("Раздел не найден")
            selected_section = Section(row["name"], bool(row["is_active"]))
            section_questions = _load_questions(
                connection,
                section_name=selected_section.name,
            )
            active_sections = []
        else:
            selected_section = None
            section_questions = []
            active_sections = [
                {
                    "section": Section(row["name"], bool(row["is_active"])),
                    "question_count": row["question_count"],
                }
                for row in connection.execute(
                    """
                    SELECT s.name, s.is_active, COUNT(q.id) AS question_count
                    FROM sections AS s
                    LEFT JOIN questions AS q ON q.section_id = s.id
                    WHERE s.is_active = 1
                    GROUP BY s.id, s.name, s.is_active
                    ORDER BY s.name
                    """
                )
            ]
    return render(
        request,
        "faq_web/section_list.html",
        {
            "sections": active_sections,
            "selected_section": selected_section,
            "questions": section_questions,
        },
    )


@require_http_methods(["GET", "POST"])
def question_create(request):
    """Показать форму и сохранить новый вопрос в SQLite."""
    with closing(_connection()) as connection:
        active_sections = [
            Section(row["name"], bool(row["is_active"]))
            for row in connection.execute(
                "SELECT name, is_active FROM sections "
                "WHERE is_active = 1 ORDER BY name"
            )
        ]
        questions = (
            _load_questions(connection) if request.method == "POST" else []
        )
        if request.method == "POST":
            author = request.POST.get("author", "").strip()
            title = request.POST.get("title", "")
            text = request.POST.get("text", "")
            section = next(
                (
                    item
                    for item in active_sections
                    if item.name == request.POST.get("section", "")
                ),
                None,
            )
            error = ""
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
                except (PermissionError, ValueError) as exception:
                    error = str(exception)
                else:
                    section_id = connection.execute(
                        "SELECT id FROM sections WHERE name = ?",
                        (section.name,),
                    ).fetchone()["id"]
                    user_id = _get_or_create_user_id(connection, author)
                    connection.execute(
                        """
                        INSERT INTO questions (
                            id, section_id, user_id, title, text, created_at,
                            status
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            question.id,
                            section_id,
                            user_id,
                            question.title,
                            question.text,
                            question.created_at.isoformat(),
                            question.status,
                        ),
                    )
                    connection.commit()
                    return redirect("faq:detail", question_id=question.id)
        else:
            error = ""

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
    """Показать вопрос и ответы, при POST сохранить ответ в SQLite."""
    with closing(_connection()) as connection:
        row = connection.execute(
            """
            SELECT q.id, q.title, q.text, q.created_at, q.status,
                   s.name AS section_name, u.name AS question_author
            FROM questions AS q
            JOIN sections AS s ON s.id = q.section_id
            JOIN users AS u ON u.id = q.user_id
            WHERE q.id = ?
            """,
            (question_id,),
        ).fetchone()
        if row is None:
            raise Http404("Вопрос не найден")
        question = Question(
            id=row["id"],
            section=row["section_name"],
            title=row["title"],
            text=row["text"],
            author=User(row["question_author"]),
            created_at=date.fromisoformat(row["created_at"]),
            status=row["status"],
        )
        question.answers = [
            Answer(
                author=User(answer["author"]),
                text=answer["text"],
                created_at=date.fromisoformat(answer["created_at"]),
            )
            for answer in connection.execute(
                """
                SELECT a.text, a.created_at, u.name AS author
                FROM answers AS a
                JOIN users AS u ON u.id = a.user_id
                WHERE a.question_id = ?
                ORDER BY a.id
                """,
                (question_id,),
            )
        ]

        error = ""
        if request.method == "POST":
            author = request.POST.get("author", "").strip()
            text = request.POST.get("text", "")
            if not author:
                error = "Укажите имя автора."
            else:
                try:
                    answer = create_answer(
                        [question],
                        role="user",
                        is_authenticated=True,
                        question_id=question_id,
                        text=text,
                        author=author,
                    )
                except (LookupError, PermissionError, ValueError) as exception:
                    error = str(exception)
                else:
                    user_id = _get_or_create_user_id(connection, author)
                    connection.execute(
                        """
                        INSERT INTO answers (
                            question_id, user_id, text, created_at
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            question_id,
                            user_id,
                            answer.text,
                            answer.created_at.isoformat(),
                        ),
                    )
                    connection.commit()
                    return redirect("faq:detail", question_id=question_id)

    return render(
        request,
        "faq_web/question_detail.html",
        {
            "question": question,
            "form_data": request.POST if request.method == "POST" else {},
            "error": error,
        },
        status=400 if error else 200,
    )


def statistics(request):
    """Показать статистику вопросов и ответов по тематическим разделам."""
    with closing(_connection()) as connection:
        sections = connection.execute(
            """
            SELECT s.name, COUNT(DISTINCT q.id) AS questions_count,
                   COUNT(a.id) AS answers_count
            FROM sections AS s
            LEFT JOIN questions AS q ON q.section_id = s.id
            LEFT JOIN answers AS a ON a.question_id = q.id
            GROUP BY s.id, s.name
            ORDER BY questions_count DESC, s.name
            """
        ).fetchall()
        totals = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM questions) AS questions_count,
                (SELECT COUNT(*) FROM answers) AS answers_count
            """
        ).fetchone()
    return render(
        request,
        "faq_web/statistics.html",
        {"sections": sections, "totals": totals},
    )
