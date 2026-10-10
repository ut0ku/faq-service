"""Проверки страниц Django-приложения FAQ."""

import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import Client, SimpleTestCase, override_settings


class FaqPagesTests(SimpleTestCase):
    """Проверить основные маршруты и отображение данных FAQ."""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_dir = Path(self.temp_dir.name)
        (self.data_dir / "data").mkdir()
        shutil.copyfile(
            settings.BASE_DIR / "data" / "faq.json",
            self.data_dir / "data" / "faq.json",
        )
        settings_override = override_settings(BASE_DIR=self.data_dir)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def test_homepage_shows_service_summary(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Сервис вопросов и ответов")
        self.assertContains(response, "Перейти к вопросам")

    def test_question_list_links_to_dynamic_detail_pages(self):
        response = self.client.get("/faq/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Как преобразовать строку в число?")
        self.assertContains(response, 'href="/faq/1/"')

    def test_question_detail_shows_answers(self):
        response = self.client.get("/faq/1/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Как из str получить int?")
        self.assertContains(response, "Используйте функцию int()")

    def test_user_can_create_question(self):
        response = self.client.post(
            "/faq/new/",
            {
                "author": "  alex  ",
                "section": "Python",
                "title": "Новый вопрос",
                "text": "Текст нового вопроса",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRegex(response.url, r"^/faq/\d+/$")
        question_response = self.client.get(response.url)
        self.assertContains(question_response, "Новый вопрос")
        self.assertContains(question_response, "alex")

    def test_invalid_question_is_not_saved(self):
        response = self.client.post(
            "/faq/new/",
            {
                "author": "alex",
                "section": "Python",
                "title": "Нет",
                "text": "Текст",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Заголовок слишком короткий",
            status_code=400,
        )
        list_response = self.client.get("/faq/")
        self.assertNotContains(list_response, "Нет")

    def test_user_can_answer_open_question(self):
        response = self.client.post(
            "/faq/1/",
            {"author": "  alex  ", "text": "Новый ответ"},
        )

        self.assertRedirects(response, "/faq/1/")
        detail_response = self.client.get("/faq/1/")
        self.assertContains(detail_response, "Новый ответ")
        self.assertContains(detail_response, "alex")

    def test_closed_question_rejects_new_answer(self):
        response = self.client.post(
            "/faq/3/",
            {"author": "alex", "text": "Ответ к закрытому вопросу"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Вопрос закрыт",
            status_code=400,
        )
        detail_response = self.client.get("/faq/3/")
        self.assertNotContains(detail_response, "Ответ к закрытому вопросу")

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_missing_question_uses_custom_404_page(self):
        response = self.client.get("/faq/99999/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Страница не найдена", status_code=404)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_unknown_url_uses_custom_404_page(self):
        response = self.client.get("/unknown/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "На главную", status_code=404)
