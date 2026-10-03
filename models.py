"""Структуры данных, используемые в сервисе FAQ."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date


def _require_mapping(value: object, entity: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Некорректные данные: {entity}")
    return value


def _require_string(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Поле {key} должно быть непустой строкой")
    return value


def _require_date(data: Mapping[str, object], key: str) -> date:
    value = _require_string(data, key)
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"Некорректная дата в поле {key}") from error


@dataclass
class User:
    """Пользователь, задающий вопрос или публикующий ответ."""

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        """Вернуть имя пользователя."""
        return self.name


@dataclass
class Section:
    """Тематический раздел, в котором публикуются вопросы."""

    name: str
    is_active: bool = True

    def __init__(self, name: str, is_active: bool = True) -> None:
        self.name = name
        self.is_active = is_active

    def to_dict(self) -> dict[str, object]:
        """Преобразовать раздел в словарь для JSON."""
        return {"name": self.name, "is_active": self.is_active}

    @classmethod
    def from_dict(cls, value: object) -> "Section":
        """Создать раздел из данных, полученных из JSON."""
        data = _require_mapping(value, "раздел")
        is_active = data.get("is_active")
        if not isinstance(is_active, bool):
            raise ValueError("Поле is_active должно быть логическим")
        return cls(_require_string(data, "name"), is_active)

    def __str__(self) -> str:
        """Вернуть название раздела."""
        return self.name


@dataclass
class Answer:
    """Ответ, прикреплённый к вопросу FAQ."""

    author: User
    text: str
    created_at: date

    def __init__(self, author: User, text: str, created_at: date) -> None:
        self.author = author
        self.text = text
        self.created_at = created_at

    def to_dict(self) -> dict[str, str]:
        """Преобразовать ответ в словарь для JSON."""
        return {
            "author": self.author.name,
            "text": self.text,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, value: object) -> "Answer":
        """Создать ответ из данных, полученных из JSON."""
        data = _require_mapping(value, "ответ")
        return cls(
            User(_require_string(data, "author")),
            _require_string(data, "text"),
            _require_date(data, "created_at"),
        )

    def __str__(self) -> str:
        """Вернуть краткое представление ответа."""
        return f"Ответ {self.author}: {self.text}"


@dataclass
class Question:
    """Вопрос вместе с ответами в сервисе FAQ."""

    id: int
    section: str
    title: str
    text: str
    author: User
    created_at: date
    status: str = "open"
    answers: list[Answer] = field(default_factory=list)

    def __init__(
        self,
        id: int,
        section: str,
        title: str,
        text: str,
        author: User,
        created_at: date,
        status: str = "open",
        answers: list[Answer] | None = None,
    ) -> None:
        self.id = id
        self.section = section
        self.title = title
        self.text = text
        self.author = author
        self.created_at = created_at
        self.status = status
        self.answers = answers if answers is not None else []

    def to_dict(self) -> dict[str, object]:
        """Преобразовать вопрос и ответы в данные для JSON."""
        return {
            "id": self.id,
            "section": self.section,
            "title": self.title,
            "text": self.text,
            "author": self.author.name,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "answers": [answer.to_dict() for answer in self.answers],
        }

    @classmethod
    def from_dict(cls, value: object) -> "Question":
        """Создать вопрос из данных, полученных из JSON."""
        data = _require_mapping(value, "вопрос")
        question_id = data.get("id")
        status = _require_string(data, "status")
        answers_data = data.get("answers")
        if type(question_id) is not int or question_id < 1:
            raise ValueError("ID вопроса должен быть положительным числом")
        if status not in {"open", "closed"}:
            raise ValueError("Некорректный статус вопроса")
        if not isinstance(answers_data, list):
            raise ValueError("Поле answers должно быть списком")
        return cls(
            id=question_id,
            section=_require_string(data, "section"),
            title=_require_string(data, "title"),
            text=_require_string(data, "text"),
            author=User(_require_string(data, "author")),
            created_at=_require_date(data, "created_at"),
            status=status,
            answers=[Answer.from_dict(answer) for answer in answers_data],
        )

    def add_answer(self, answer: Answer) -> None:
        """Добавить ответ, если обсуждение ещё открыто."""
        if self.status == "closed":
            raise ValueError("Вопрос закрыт, ответить нельзя")
        self.answers.append(answer)

    def close(self) -> None:
        """Закрыть обсуждение вопроса."""
        if self.status == "closed":
            raise ValueError("Обсуждение уже закрыто")
        self.status = "closed"

    def __str__(self) -> str:
        """Вернуть краткое представление вопроса."""
        return (
            f"[{self.id}] {self.title} "
            f"({self.status}, {self.section}, {self.author})"
        )


def create_initial_data() -> tuple[list[Section], list[Question]]:
    """Вернуть исходный сценарий ПР1 в виде данных для правки."""
    section = Section(name="Python")
    question = Question(
        id=1,
        section=section.name,
        title="Как преобразовать строку в число?",
        text="Как из str получить int?",
        author=User("maria_smirnova"),
        created_at=date(2026, 9, 15),
        answers=[
            Answer(
                author=User("ivan_petrov"),
                text="Используйте функцию int(), например: int('42')",
                created_at=date(2026, 9, 16),
            )
        ],
    )
    return [section], [question]
