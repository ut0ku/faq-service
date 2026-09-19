"""Initial scenario for the FAQ Service (PR1)."""

from datetime import date


# --- Исходные данные ---

section_title = "Python"
section_is_active = True

question_title = "Как преобразовать строку в число?"
question_author = "maria_smirnova"
question_status = "open"          # open | closed
question_created_at = date(2026, 9, 15)

answer_text = "Используйте функцию int(), например: int('42')"
answer_author = "ivan_petrov"
answer_created_at = date(2026, 9, 16)

current_username = "ivan_petrov"
current_role = "user"             # guest | user | admin


# --- Функции ---

def get_role_permissions(role: str) -> str:
    """Return human-readable description of the role permissions."""
    if role == "guest":
        return "Гость: может только просматривать вопросы и ответы"
    if role == "user":
        return "Пользователь: может создавать вопросы и отвечать на них"
    if role == "admin":
        return "Админ: права пользователя + модерация обсуждений"
    return "Неизвестная роль"


def create_question(role: str, is_authenticated: bool,
                    section_is_active_flag: bool,
                    title: str, text: str) -> str:
    """Validate and create a question depending on the role."""
    if not is_authenticated:
        return "Ошибка: необходимо авторизоваться"
    if role == "guest":
        return "Ошибка: гость не может создавать вопросы"
    if role != "user" and role != "admin":
        return "Ошибка: недостаточно прав для создания вопроса"
    if not section_is_active_flag:
        return "Ошибка: раздел закрыт для публикации вопросов"
    stripped_title = title.strip()
    stripped_text = text.strip()
    if len(stripped_title) == 0 or len(stripped_text) == 0:
        return "Ошибка: заголовок и текст вопроса не могут быть пустыми"
    if len(stripped_title) < 5:
        return "Ошибка: заголовок слишком короткий (минимум 5 символов)"
    return f"Вопрос «{stripped_title}» успешно создан"


def create_answer(role: str, is_authenticated: bool,
                  question_status_flag: str, text: str) -> str:
    """Validate and create an answer depending on the role and question status."""
    if not is_authenticated:
        return "Ошибка: необходимо авторизоваться"
    if role == "guest":
        return "Ошибка: гость не может отвечать на вопросы"
    if role != "user" and role != "admin":
        return "Ошибка: недостаточно прав для ответа"
    if question_status_flag == "closed":
        return "Ошибка: вопрос закрыт, ответить нельзя"
    stripped_text = text.strip()
    if len(stripped_text) == 0:
        return "Ошибка: текст ответа не может быть пустым"
    return "Ответ успешно добавлен"


def close_question(role: str, question_status_flag: str) -> str:
    """Close a question discussion. Available to admin only."""
    if role != "admin":
        return "Ошибка: закрывать обсуждение может только администратор"
    if question_status_flag == "closed":
        return "Обсуждение уже закрыто"
    return "Обсуждение закрыто администратором"


def get_question_age(created: date, reference: date) -> str:
    """Describe how long ago the question was created."""
    days_passed = (reference - created).days
    if days_passed < 0:
        return "Ошибка: дата создания вопроса в будущем"
    if days_passed == 0:
        return "Вопрос создан сегодня"
    return f"Вопрос создан {days_passed} дн. назад"


# --- Демонстрация сценария ---

print("=== Сервис организации FAQ (начальный сценарий) ===")
print(f"Раздел: {section_title} (активен: {section_is_active})")
print(f"Текущий пользователь: {current_username}")
print(get_role_permissions(current_role))
print()

print(f"Вопрос: {question_title}")
print(f"Автор вопроса: {question_author}")
print(f"Статус вопроса: {question_status}")
print(get_question_age(question_created_at, date(2026, 9, 19)))
print()

print(create_question(current_role, True, section_is_active,
                      question_title, "Как из str получить int?"))
print(create_answer(current_role, True, question_status, answer_text))
print()

print("--- Сценарий гостя ---")
current_role = "guest"
print(get_role_permissions(current_role))
print(create_question(current_role, True, section_is_active,
                      question_title, "Как из str получить int?"))
print(create_answer(current_role, True, question_status, answer_text))
print(close_question(current_role, question_status))
print()

print("--- Сценарий администратора ---")
current_role = "admin"
print(get_role_permissions(current_role))
print(create_answer(current_role, True, question_status, answer_text))
print(close_question(current_role, question_status))
print(close_question(current_role, question_status))
print()

print("--- Попытка ответить на закрытый вопрос ---")
question_status = "closed"
current_role = "user"
print(create_answer(current_role, True, question_status, answer_text))