"""Перенос прежней SQLite-базы FAQ в базу, настроенную для Django."""

import sqlite3
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from faq_web.models import Answer, Question, Section, User


class Command(BaseCommand):
    """Импортировать данные из data/faq.sqlite3, не изменяя исходную базу."""

    help = "Переносит данные FAQ из прежней SQLite-базы в базу Django."

    def handle(self, *args: object, **options: object) -> None:
        source_path = Path(settings.BASE_DIR) / "data" / "faq.sqlite3"
        if not source_path.is_file():
            raise CommandError(f"Исходная база не найдена: {source_path}")

        if any(
            model.objects.exists()
            for model in (Section, User, Question, Answer)
        ):
            raise CommandError(
                "Целевая база уже содержит данные FAQ; импорт отменён."
            )

        source_uri = f"file:{source_path.resolve().as_posix()}?mode=ro"
        try:
            with sqlite3.connect(source_uri, uri=True) as connection:
                connection.row_factory = sqlite3.Row
                sections = connection.execute(
                    "SELECT id, name, is_active FROM sections ORDER BY id"
                ).fetchall()
                users = connection.execute(
                    "SELECT id, name FROM users ORDER BY id"
                ).fetchall()
                questions = connection.execute(
                    """
                    SELECT id, section_id, user_id, title, text, created_at,
                           status
                    FROM questions ORDER BY id
                    """
                ).fetchall()
                answers = connection.execute(
                    """
                    SELECT id, question_id, user_id, text, created_at
                    FROM answers ORDER BY id
                    """
                ).fetchall()
        except sqlite3.Error as error:
            raise CommandError(
                f"Не удалось прочитать исходную базу {source_path}: {error}"
            ) from error

        try:
            with transaction.atomic():
                Section.objects.bulk_create(
                    [
                        Section(
                            pk=row["id"],
                            name=row["name"],
                            is_active=bool(row["is_active"]),
                        )
                        for row in sections
                    ]
                )
                User.objects.bulk_create(
                    [User(pk=row["id"], name=row["name"]) for row in users]
                )
                Question.objects.bulk_create(
                    [
                        Question(
                            pk=row["id"],
                            section_id=row["section_id"],
                            author_id=row["user_id"],
                            title=row["title"],
                            text=row["text"],
                            created_at=date.fromisoformat(row["created_at"]),
                            status=row["status"],
                        )
                        for row in questions
                    ]
                )
                Answer.objects.bulk_create(
                    [
                        Answer(
                            pk=row["id"],
                            question_id=row["question_id"],
                            author_id=row["user_id"],
                            text=row["text"],
                            created_at=date.fromisoformat(row["created_at"]),
                        )
                        for row in answers
                    ]
                )
        except (ValueError, KeyError) as error:
            raise CommandError(
                f"Некорректные данные в исходной базе: {error}"
            ) from error

        self.stdout.write(
            self.style.SUCCESS(
                "Перенесено: "
                f"{len(sections)} разделов, {len(users)} пользователей, "
                f"{len(questions)} вопросов, {len(answers)} ответов."
            )
        )
