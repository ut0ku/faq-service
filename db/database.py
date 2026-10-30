"""Подключение к базе данных SQLite."""

import sqlite3
from pathlib import Path

from django.conf import settings

PROJECT_DIR = Path(__file__).resolve().parent.parent


def get_database_path() -> Path:
    """Вернуть путь к SQLite-базе Django-приложения."""
    base_dir = Path(settings.BASE_DIR) if settings.configured else PROJECT_DIR
    return base_dir / "data" / "faq.sqlite3"


def get_connection() -> sqlite3.Connection:
    """Создать подключение с внешними ключами и именованными строками."""
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_database() -> None:
    """Создать схему и импортировать JSON при первом запуске приложения."""
    connection = get_connection()
    try:
        table = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name = 'questions'"
        ).fetchone()
        if table is not None:
            return

        schema_path = PROJECT_DIR / "sql" / "schema.sql"
        connection.executescript(
            schema_path.read_text(encoding="utf-8")
        )

        from db.import_json import import_data

        json_path = Path(settings.BASE_DIR) / "data" / "faq.json"
        import_data(connection, json_path)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
