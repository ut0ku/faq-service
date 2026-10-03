"""Тесты бизнес-операций FAQ и хранения данных в JSON."""

import json
from datetime import date

import pytest

import main as faq_app
from models import Answer, Question, Section, User, create_initial_data
from questions import (
    close_question,
    create_answer,
    create_question,
    iter_questions,
    search_questions,
    sort_questions,
)
from storage import StorageError, load_data, save_data


def test_create_question_adds_record_with_next_id() -> None:
    sections, questions = create_initial_data()

    question = create_question(
        questions,
        sections[0],
        "user",
        True,
        "Новый вопрос",
        "Текст вопроса",
        "ivan_petrov",
        date(2026, 9, 20),
    )

    assert question.id == 2
    assert question in questions


def test_guest_cannot_create_question() -> None:
    with pytest.raises(PermissionError, match="Гость"):
        create_question(
            [], Section("Python"), "guest", True, "Заголовок", "Текст", "guest"
        )


def test_answer_can_be_added_to_open_question_only() -> None:
    _, questions = create_initial_data()

    answer = create_answer(
        questions, "user", True, 1, "  Дополнение  ", "ivan_petrov"
    )

    assert answer.text == "Дополнение"
    assert questions[0].answers[-1] == answer
    questions[0].status = "closed"
    with pytest.raises(ValueError, match="Вопрос закрыт"):
        create_answer(questions, "user", True, 1, "Еще ответ", "ivan_petrov")


def test_admin_can_close_question() -> None:
    _, questions = create_initial_data()

    close_question("admin", questions[0])

    assert questions[0].status == "closed"


def test_models_represent_authors_and_own_question_behavior() -> None:
    _, questions = create_initial_data()
    question = questions[0]
    answer = Answer(User("anna"), "Полезный ответ", date(2026, 9, 20))

    question.add_answer(answer)
    assert isinstance(question.author, User)
    assert isinstance(answer.author, User)
    assert all(
        "__init__" in model.__dict__
        for model in (User, Section, Answer, Question)
    )
    assert str(Section("Python")) == "Python"
    assert str(question).startswith("[1] Как преобразовать")
    assert str(answer) == "Ответ anna: Полезный ответ"

    question.close()
    assert question.status == "closed"
    with pytest.raises(ValueError, match="Вопрос закрыт"):
        question.add_answer(answer)


def test_search_generator_and_sorting() -> None:
    sections, questions = create_initial_data()
    create_question(
        questions,
        sections[0],
        "user",
        True,
        "Вопрос про списки",
        "Как работать со списками?",
        "maria_smirnova",
        date(2026, 9, 20),
    )

    assert [item.id for item in iter_questions(questions, "open")] == [1, 2]
    assert [item.id for item in search_questions("списки", questions)] == [2]
    assert [item.id for item in sort_questions(questions)] == [2, 1]


def test_json_round_trip(tmp_path) -> None:
    sections, questions = create_initial_data()
    file_path = tmp_path / "faq.json"

    save_data(file_path, sections, questions)

    assert load_data(file_path) == (sections, questions)


def test_invalid_json_data_raises_storage_error(tmp_path) -> None:
    file_path = tmp_path / "faq.json"
    file_path.write_text(json.dumps({"sections": [], "questions": [None]}))

    with pytest.raises(StorageError, match="Некорректный формат"):
        load_data(file_path)


def test_menu_workflow_persists_all_changes(
    tmp_path, monkeypatch, capsys
) -> None:
    file_path = tmp_path / "faq.json"
    actions = iter(
        [
            "1",
            "2",
            "Python",
            "Вопрос про списки",
            "Как работать со списками?",
            "5",
            "списки",
            "6",
            "admin_user",
            "admin",
            "3",
            "2",
            "Используйте list.",
            "4",
            "2",
            "1",
            "7",
            "0",
        ]
    )
    monkeypatch.setattr(faq_app, "DATA_FILE", file_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(actions))

    faq_app.main()

    _, questions = load_data(file_path)
    assert questions[1].status == "closed"
    assert questions[1].answers[0].text == "Используйте list."
    assert "Функции модуля questions" in capsys.readouterr().out
