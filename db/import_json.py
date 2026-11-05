"""Перенос данных FAQ из JSON в SQLite."""

from pathlib import Path
import sqlite3

from db.database import PROJECT_DIR, get_connection
from storage import load_data


def import_data(connection: sqlite3.Connection, json_path: Path) -> None:
    """Импортировать разделы, вопросы, авторов и ответы в одну транзакцию."""
    # Проверка на повторный импорт
    existing_questions = connection.execute(
        "SELECT COUNT(*) FROM questions"
    ).fetchone()[0]
    if existing_questions:
        raise ValueError(
            "База уже содержит вопросы. Удалите faq.sqlite3 перед повторным "
            "импортом."
        )

    # Загрузка данных из JSON
    sections, questions = load_data(json_path)
    # Создание разделов и авторов, на которых будут ссылки
    connection.executemany(
        "INSERT INTO sections (name, is_active) VALUES (?, ?)",
        [(section.name, int(section.is_active)) for section in sections],
    )

    # сбор и импорт пользователей
    user_names = set()
    for question in questions:
        user_names.add(question.author.name)
        for answer in question.answers:
            user_names.add(answer.author.name)

    # Сохранение id пользователей для внешних ключей
    users = {}
    for name in user_names:
        cursor = connection.execute(
            "INSERT INTO users (name) VALUES (?)",
            (name,),
        )
        if cursor.lastrowid is None:
            raise RuntimeError(f"Не удалось сохранить пользователя «{name}».")
        users[name] = cursor.lastrowid

    for question in questions:
        section_id = connection.execute(
            "SELECT id FROM sections WHERE name = ?",
            (question.section,),
        ).fetchone()
        if section_id is None:
            raise ValueError(
                f"Для вопроса {question.id} не найден раздел "
                f"«{question.section}»."
            )
        # импорт разделов
        connection.execute(
            """
            INSERT INTO questions (
                id, section_id, user_id, title, text, created_at, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question.id,
                section_id["id"],
                users[question.author.name],
                question.title,
                question.text,
                question.created_at.isoformat(),
                question.status,
            ),
        )
        connection.executemany(
            """
            INSERT INTO answers (question_id, user_id, text, created_at)
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    question.id,
                    users[answer.author.name],
                    answer.text,
                    answer.created_at.isoformat(),
                )
                for answer in question.answers
            ],
        )


def main() -> None:
    """Создать схему и выполнить первоначальный импорт из data/faq.json."""
    schema_path = PROJECT_DIR / "sql" / "schema.sql"
    connection = get_connection()
    try:
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        import_data(connection, PROJECT_DIR / "data" / "faq.json")
        # Подтверждаем импорт только после успешной вставки всех данных
        connection.commit()
    except Exception:
        # Отменяем частичный импорт при ошибке
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
