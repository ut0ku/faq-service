"""Загрузка и сохранение данных FAQ в JSON-файлах."""

import json
from pathlib import Path

from models import Question, Section


class StorageError(Exception):
    """Ошибка чтения или записи данных FAQ."""


def load_data(path: str | Path) -> tuple[list[Section], list[Question]]:
    """Прочитать и проверить разделы и вопросы из JSON-файла."""
    file_path = Path(path)
    try:
        with file_path.open("r", encoding="utf-8") as data_file:
            payload = json.load(data_file)
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(
            f"Не удалось прочитать {file_path}: {error}"
        ) from error

    try:
        if not isinstance(payload, dict):
            raise ValueError("Корневой элемент JSON должен быть объектом")
        sections_data = payload.get("sections")
        questions_data = payload.get("questions")
        if not isinstance(sections_data, list):
            raise ValueError("Поле sections должно быть списком")
        if not isinstance(questions_data, list):
            raise ValueError("Поле questions должно быть списком")
        sections = [Section.from_dict(item) for item in sections_data]
        questions = [Question.from_dict(item) for item in questions_data]
    except ValueError as error:
        raise StorageError(
            f"Некорректный формат данных в {file_path}: {error}"
        ) from error
    return sections, questions


def save_data(
    path: str | Path,
    sections: list[Section],
    questions: list[Question],
) -> None:
    """Записать записи FAQ в читаемый JSON в кодировке UTF-8."""
    file_path = Path(path)
    payload = {
        "sections": [section.to_dict() for section in sections],
        "questions": [question.to_dict() for question in questions],
    }
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8") as data_file:
            json.dump(payload, data_file, ensure_ascii=False, indent=2)
            data_file.write("\n")
    except OSError as error:
        raise StorageError(
            f"Не удалось сохранить {file_path}: {error}"
        ) from error
