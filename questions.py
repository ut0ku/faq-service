"""Бизнес-операции над вопросами и ответами FAQ."""

from collections.abc import Iterable, Iterator
from datetime import date

from models import Answer, Question, Section, User

ROLE_PERMISSIONS = {
    "guest": "Гость: может только просматривать вопросы и ответы",
    "user": "Пользователь: может создавать вопросы и отвечать на них",
    "admin": "Админ: права пользователя + модерация обсуждений",
}


def get_role_permissions(role: str) -> str:
    """Вернуть понятное описание прав роли."""
    normalized_role = (role or "").strip().casefold()
    return ROLE_PERMISSIONS.get(normalized_role, "Неизвестная роль")


def create_question(
    questions: list[Question],
    section: Section,
    role: str,
    is_authenticated: bool,
    title: str,
    text: str,
    author: str,
    created_at: date | None = None,
) -> Question:
    """Проверить и добавить вопрос, вернуть созданную запись."""
    normalized_role = (role or "").strip().casefold()
    if not is_authenticated:
        raise PermissionError("Необходимо авторизоваться")
    if normalized_role == "guest":
        raise PermissionError("Гость не может создавать вопросы")
    if normalized_role not in {"user", "admin"}:
        raise PermissionError("Недостаточно прав для создания вопроса")
    if not section.is_active:
        raise ValueError("Раздел закрыт для публикации вопросов")

    clean_title = title.strip()
    clean_text = text.strip()
    if not clean_title or not clean_text:
        raise ValueError("Заголовок и текст не могут быть пустыми")
    if len(clean_title) < 5:
        raise ValueError("Заголовок слишком короткий (минимум 5 символов)")

    question = Question(
        id=max((item.id for item in questions), default=0) + 1,
        section=section.name,
        title=clean_title,
        text=clean_text,
        author=User(author),
        created_at=created_at or date.today(),
    )
    questions.append(question)
    return question


def find_question(question_id: int, questions: Iterable[Question]) -> Question:
    """Найти вопрос по ID или сообщить, что его нет."""
    for question in questions:
        if question.id == question_id:
            return question
    raise LookupError(f"Вопрос с ID {question_id} не найден")


def create_answer(
    questions: Iterable[Question],
    role: str,
    is_authenticated: bool,
    question_id: int,
    text: str,
    author: str,
    created_at: date | None = None,
) -> Answer:
    """Проверить и прикрепить ответ к открытому вопросу."""
    normalized_role = (role or "").strip().casefold()
    if not is_authenticated:
        raise PermissionError("Необходимо авторизоваться")
    if normalized_role == "guest":
        raise PermissionError("Гость не может отвечать на вопросы")
    if normalized_role not in {"user", "admin"}:
        raise PermissionError("Недостаточно прав для ответа")

    question = find_question(question_id, questions)
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("Текст ответа не может быть пустым")

    answer = Answer(User(author), clean_text, created_at or date.today())
    question.add_answer(answer)
    return answer


def close_question(role: str, question: Question) -> None:
    """Закрыть обсуждение; это доступно только администратору."""
    if (role or "").strip().casefold() != "admin":
        raise PermissionError(
            "Закрывать обсуждение может только администратор"
        )
    question.close()


def iter_questions(
    questions: Iterable[Question], status: str | None = None
) -> Iterator[Question]:
    """Возвращать вопросы, при необходимости фильтруя по статусу."""
    normalized_status = None if status is None else status.strip().casefold()
    for question in questions:
        if normalized_status is None or question.status == normalized_status:
            yield question


def search_questions(
    query: str,
    questions: Iterable[Question],
) -> list[Question]:
    """Искать по заголовкам, текстам, разделам, авторам и ответам."""
    search_term = str(query).strip().casefold()
    if not search_term:
        return list(questions)
    matches = []
    for question in questions:
        searchable_text = " ".join(
            [
                question.title,
                question.text,
                question.section,
                question.author.name,
                *(answer.text for answer in question.answers),
            ]
        ).casefold()
        if search_term in searchable_text:
            matches.append(question)
    return matches


def sort_questions(questions: Iterable[Question]) -> list[Question]:
    """Отсортировать вопросы: сначала новые, затем по ID."""
    return sorted(
        questions,
        key=lambda question: (question.created_at, question.id),
        reverse=True,
    )


def get_question_age(created: date, reference: date) -> str:
    """Описать, сколько времени прошло с создания вопроса."""
    days_passed = (reference - created).days
    if days_passed < 0:
        return "Ошибка: дата создания вопроса в будущем"
    if days_passed == 0:
        return "Вопрос создан сегодня"
    return f"Вопрос создан {days_passed} дн. назад"
