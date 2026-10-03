"""Консольное приложение для работы с вопросами и ответами FAQ."""

from pathlib import Path
from datetime import date

import questions as question_service
from models import Question, Section, create_initial_data
from questions import (
    close_question,
    create_answer,
    create_question,
    find_question,
    get_question_age,
    get_role_permissions,
    iter_questions,
    search_questions,
    sort_questions,
)
from storage import StorageError, load_data, save_data
from utils import iter_public_functions

DATA_FILE = Path(__file__).resolve().parent / "data" / "faq.json"
ROLES = {"guest", "user", "admin"}


def _find_section(sections: list[Section], name: str) -> Section:
    """Вернуть раздел по имени или сообщить, что его нет."""
    for section in sections:
        if section.name.casefold() == name.casefold():
            return section
    raise ValueError("Раздел не найден")


def _show_questions(questions: list[Question]) -> None:
    """Вывести вопросы в обратном хронологическом порядке."""
    question_list = sort_questions(iter_questions(questions))
    if not question_list:
        print("Вопросов пока нет.")
        return

    for question in question_list:
        print(question)
        print(f"  {question.text}")
        print(f"  {get_question_age(question.created_at, date.today())}")
        for answer in question.answers:
            print(f"  {answer}")


def _show_help() -> None:
    """Показать публичные функции сервиса через интроспекцию."""
    print("Функции модуля questions:")
    for description in iter_public_functions(question_service):
        print(f"  {description}")


def _save(sections: list[Section], questions: list[Question]) -> None:
    """Сохранить текущие данные из памяти."""
    save_data(DATA_FILE, sections, questions)


def main() -> None:
    """Загрузить данные FAQ и запустить интерактивное меню."""
    if DATA_FILE.exists():
        try:
            sections, questions = load_data(DATA_FILE)
        except StorageError as error:
            print(f"Ошибка загрузки данных: {error}")
            return
    else:
        sections, questions = create_initial_data()

    username = "ivan_petrov"
    role = "user"
    print("=== Сервис организации FAQ ===")
    print(get_role_permissions(role))

    try:
        while True:
            print(
                "\n1. Показать вопросы\n"
                "2. Создать вопрос\n"
                "3. Ответить на вопрос\n"
                "4. Закрыть обсуждение\n"
                "5. Найти вопросы\n"
                "6. Сменить пользователя или роль\n"
                "7. Справка о функциях\n"
                "0. Сохранить и выйти"
            )
            choice = input("Выберите пункт меню: ").strip()

            try:
                if choice == "1":
                    _show_questions(questions)
                elif choice == "2":
                    section_name = input("Раздел: ").strip()
                    section = _find_section(sections, section_name)
                    question = create_question(
                        questions,
                        section,
                        role,
                        True,
                        input("Заголовок: "),
                        input("Текст вопроса: "),
                        username,
                    )
                    _save(sections, questions)
                    print(f"Вопрос [{question.id}] создан и сохранен.")
                elif choice == "3":
                    question_id = int(input("ID вопроса: "))
                    answer = create_answer(
                        questions,
                        role,
                        True,
                        question_id,
                        input("Текст ответа: "),
                        username,
                    )
                    _save(sections, questions)
                    print(f"Ответ добавлен: {answer.text}")
                elif choice == "4":
                    question_id = int(input("ID вопроса: "))
                    question = find_question(question_id, questions)
                    close_question(role, question)
                    _save(sections, questions)
                    print("Обсуждение закрыто.")
                elif choice == "5":
                    query = input("Поиск: ").strip()
                    _show_questions(search_questions(query, questions))
                elif choice == "6":
                    username = input("Имя пользователя: ").strip()
                    if not username:
                        raise ValueError(
                            "Имя пользователя не может быть пустым"
                        )
                    selected_role = input("Роль (guest/user/admin): ").strip()
                    if selected_role not in ROLES:
                        raise ValueError("Неизвестная роль")
                    role = selected_role
                    print(get_role_permissions(role))
                elif choice == "7":
                    _show_help()
                elif choice == "0":
                    _save(sections, questions)
                    print("Данные сохранены. До свидания!")
                    return
                else:
                    print("Выберите пункт меню от 0 до 7.")
            except (LookupError, PermissionError, ValueError) as error:
                print(f"Ошибка: {error}")
            except StorageError as error:
                print(f"Ошибка сохранения данных: {error}")
    except (EOFError, KeyboardInterrupt):
        print(
            "\nРабота завершена без сохранения последних изменений."
        )


if __name__ == "__main__":
    main()
